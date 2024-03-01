from boxsdk import BoxAPIException, JWTAuth, Client                             # Box API
from boxsdk.object.search import MetadataSearchFilter, MetadataSearchFilters    # querying by metadata
import requests                                                                 # IAM affiliations removed date filter, IAM get status
from datetime import datetime, timedelta, timezone                              # retrieving today's date
from datetime import date                                                       # comparing the "cutoff" date to affiliation_removed_date
from time import sleep                                                          # stall 300s for transfer errors, retry 60s for move errors
import csv                                                                      # reading / writing to the CSV files  
import logging                                                                  # to log critical errors
import sys                                                                      # to terminate the program after critical errors
import secret_credentials                                                       # file containing UCSB IAM secrets


url_base = 'https://eis.identity.ucsb.edu/.' 
iam_headers = { "Authorization" : 'Bearer {}'.format(secret_credentials.generate_iamtesttoken()) }

box_config = JWTAuth.from_settings_file('PROD_config.json') 
client = Client(box_config)
service_account = client.user().get()
print(f'Service Account user ID is {service_account.id}')


def replace_iam_access_token():
    # generate a new IAM access token
    global iam_headers
    iamtesttoken = secret_credentials.generate_iamtesttoken()
    iam_headers = { "Authorization" : 'Bearer {}'.format(iamtesttoken) }
    print("new access token created (inside replace_iam_access_token)", iamtesttoken)


def create_giant_cabinet(public_storage_client, giant_cabinet_id: str):
    print("The create_giant_cabinet() function is designed to create ONE giant cabinet folder in the Box Archive.")
    print("create_giant_cabinet() creates a folder called \"Giant Cabinet\" that holds all the shared file/folder data.")
    print("Folder Structure: giant cabinet -> userid_ucsbnetid_drawer -> date of when program was run -> user files/folders")
    
    try: 
        # Retrieving the giant cabinet folder from the Box Archive account
        giant_cabinet = public_storage_client.folder(folder_id=giant_cabinet_id).get() 
        print("Giant Cabinet Already Exists!")
        return giant_cabinet_id 
    
    except: 
        # Create a giant cabinet folder with static folder id in the Box Archive account
        giant_cabinet = public_storage_client.folder('0').create_subfolder("Giant Cabinet")
        print("^Ignore the above error message. Giant Cabinet was not found. New Giant Cabinet has been created.")
        print("SAVE THIS INFORMATION! ID of Giant Cabinet:", giant_cabinet.id, "REPLACE the id in __main__!")
        return giant_cabinet.id


def create_big_drawer(user_net_id, ucsb_campus_id, giant_cabinet_id, public_storage_client):
    # Try creating a user drawer in the giant cabinet.
    # If the user drawer already exists, then find the folder with regular query or metadata query.
    # Set metadata for the user drawer.  
    # Try creating a date folder inside the user drawer. 
    # If the date folder already exists, then try making a date folder following the convention: MM-DD-YY (#)
    # For example, if 07-10-23 already exists, then try making 07-10-23 (1). If 07-10-23 (1) already exists
    # then try making 7-10-23 (2) ... up until 07-10-23 (20)

    name_of_file_drawer = str(user_net_id) + "_" + str(ucsb_campus_id) + "_drawer"

    try: 
        big_drawer = public_storage_client.folder(giant_cabinet_id).create_subfolder(name_of_file_drawer)
    
    except BoxAPIException as box_api_exception:
        if box_api_exception.status == 409 and box_api_exception.message == 'Item with the same name already exists':
            print("Drawer already exists:", name_of_file_drawer)

            ancestor_folder_id = ["ANCESTOR_FOLDER_ID"]
            query_str = "\"" + name_of_file_drawer + "\""
            print(query_str)
            collection = public_storage_client.search().query(
                query= query_str, 
                content_type="name", 
                ancestor_folder_ids=ancestor_folder_id, 
                type="folder"
            )

            for folder in collection:
                print(folder.name, "vs", name_of_file_drawer)
                if folder.name == name_of_file_drawer:
                    print("Found match in regular query matching")
                    big_drawer = folder
                    break 
            
            if big_drawer is not None:
                print("The drawer already exists.", "big drawer id:", big_drawer.id)
            else:
                # Use metadata query to find the user's folder
                metadata_search_filter = MetadataSearchFilter(template_key='foldermetadata', scope='enterprise')
                metadata_search_filter.add_value_based_filter(field_key='drawerName', value=name_of_file_drawer)
                metadata_search_filters = MetadataSearchFilters()
                metadata_search_filters.add_filter(metadata_search_filter)

                metadata_query_result = public_storage_client.search().query(None, limit=100, offset=0, metadata_filters=metadata_search_filters)
                print(f"Metadata Query Results {metadata_query_result}")

                for folder in metadata_query_result:
                    print(folder.name, "vs", name_of_file_drawer)
                    if folder.name == name_of_file_drawer:
                        print("Found match in metadata query matching")
                        big_drawer = folder
                        break
                    
                # Could not find the associated big_drawer for a user
                # Return the big_drawer.id as 0, representing the Box Archive root director
                if big_drawer is None:
                    print("ERROR: Could NOT find the associated big drawer")
                    return "0"

        else:
            logging.critical("A serious error has occurred while creating big_drawer!")
            sys.exit(1)

    # Set drawerName metadata containing the name of the file drawer on every user's drawer
    try: 
        metadata = {
            'drawerName': str(name_of_file_drawer),
        }

        applied_metadata = public_storage_client.folder(big_drawer.id).metadata(scope='enterprise', template='foldermetadata').set(metadata)

        print("Metadata successfully applied on big drawer id:", big_drawer.id)

    except BoxAPIException as box_api_exception:
        print("Box API Exception when trying to set metadata")

    # Add a drawer section with date stamp of when the program was run (in case user is offboarded twice)
    # Set fixed offset for PST (UTC-8), ChatGPT assisted
    pst_offset = timedelta(hours=-8)
    utc_now = datetime.now(timezone.utc)
    current_time_pst = utc_now + pst_offset

    date_of_retrieval = str(current_time_pst.year) + "-" + str(current_time_pst.month) + "-" + str(current_time_pst.day)
    print("Date of retrieval:", date_of_retrieval)

    try:
        date_folder = public_storage_client.folder(big_drawer.id).create_subfolder(date_of_retrieval)
    except BoxAPIException as box_api_exception:
        if box_api_exception.status  == 409 and box_api_exception.message == 'Item with the same name already exists':
            print("Date folder already exists")

            # I set the maximum number of runs on a given day to be 20. Folder(1), Folder(2), Folder(3), etc.
            max_runs = 20
            for i in range(1, max_runs + 1):
                try: 
                    date_folder = public_storage_client.folder(big_drawer.id).create_subfolder((date_of_retrieval + "(" + str(i) + ")"))
                    break
                except BoxAPIException as box_api_exception:
                    if box_api_exception.status  == 409 and box_api_exception.message == 'Item with the same name already exists':
                        print("Failed to create folder with name:", date_of_retrieval + "(" + str(i) + ")")
                        if i == max_runs:
                            logging.critical("The current maximum of runs per day is set to " + str(max_runs) + ".")
                            sys.exit(2)
                    else: 
                        logging.critical("A serious error has occurred while creating date_folder " + str(i))
                        sys.exit(1)
        else:
            logging.critical("A serious error has occurred while creating the date_folder!")
            sys.exit(1)
    
    return date_folder.id


def move_to_date_folder(public_storage_client, transfer_folder_id, date_folder_id, read_me_file_id):
    # Move the folder into the date folder
    folder_to_move = public_storage_client.folder(transfer_folder_id)
    date_folder_destination = public_storage_client.folder(date_folder_id)
    moved_folder = folder_to_move.move(date_folder_destination)
    print(f'Folder "{moved_folder.name}" has been moved into folder "{moved_folder.parent.name}"')

    # Copy a file titled "READ ME IMPORTANT" into the collaborated folder 
    read_me_file = (public_storage_client.file(read_me_file_id)).copy(parent_folder=folder_to_move)
    print(f'Read Me File: "{read_me_file.name}" has been copied into folder "{read_me_file.parent.name}"')

    # Add a folder description to the collaborated folder 
    read_me_desc_folder = public_storage_client.folder(folder_id=moved_folder.id).update_info(data={
        'description': 'The owner of the items is no longer associated with University of California, Santa Barbara. Ownership of the folder has been temporarily transferred to the Box Archive. To request ownership permissions of the folder, please message help@lsit.ucsb.edu.'
    })


def get_affiliations_removed_users(dateFilter, cutoff_date):
    '''
    cutoff date should be later than the dateFilter
    example: if dateFiler is 2023-07-01, cutoff date is 2023-07-20
    then program will retrieve all the users with affiliations removed from 2023-07-01 to 2023-07-20 (inclusive)
    
    example usage: 
    # Set a 6 month delay to not catch individuals who are in the middle of onboarding
    # print(get_affiliations_removed_users(dateFilter="2023-07-01", cutoff_date="2023-07-05"))
    '''
    # dateFilter: 0000-00-00 | year, month, date
    cutoff_year = int(cutoff_date[:4])
    cutoff_month = int(cutoff_date[5:7])
    cutoff_day = int(cutoff_date[8:])
    datetime_cutoff_date = date(cutoff_year, cutoff_month, cutoff_day)

    # Concatenate base URL and request URL
    request_url = "{}/affiliate/readonly/affiliations/removed?dateFilter={}".format(url_base, dateFilter)
    response = requests.get(request_url, headers=iam_headers)

    # Speed up affiliations request with json + dictionary instead of parsing through strings
    content_list = response.json()

    data_dict = {}

    for dic in content_list:
        net_id = dic['netId']
        affiliations_removed_date = dic['lastAffiliationRemovedDate']

        aff_rem_year = int(affiliations_removed_date[:4])
        aff_rem_month = int(affiliations_removed_date[5:7])
        aff_rem_day = int(affiliations_removed_date[8:])

        datetime_affiliations_removed_date = date(aff_rem_year, aff_rem_month, aff_rem_day)
        
        # Comparing the dates, proceed if affiliation removed date is EARLIER OR EQUAL to the cutoff date
        if datetime_affiliations_removed_date <= datetime_cutoff_date:
            print("Proceeded with affiliation removed date:", datetime_affiliations_removed_date)

            request_url = url_base + "/people/readonly/" + net_id + "/status"
            req = requests.get(request_url, headers=iam_headers)
            tempList=req.text.split(":")

            try:
                # Sometimes you get a Forbidden HTML string as tempList, skip the user if we get "forbidden" 
                tempItem=tempList[2]
                statusStr=tempItem.rstrip(tempItem[-1])

                if statusStr == '"activated"' or statusStr == '"renew"' or statusStr == '"created"' or statusStr == "null":
                    data_dict[net_id] = {
                        'terminated': False
                    }
                elif statusStr == '"separated"' or statusStr == '"terminated"':
                    data_dict[net_id] = {
                        'terminated': True
                    }
                    print("terminated account", net_id)

            except:
                print("AN ERROR AS OCCURED:", net_id, "\n", req, "\n", tempList)

        else:
            print("Did not proceed with affiliation removed date:", datetime_affiliations_removed_date)
    
    return data_dict


def iam_get_status(ucsbNetId):
    # Concatenate base URL and request URL
    request_url = "{}/people/readonly/{}/status".format(url_base, ucsbNetId)
    response = requests.get(request_url, headers=iam_headers)
    try:
        content_list = response.json()
    except:
        return "Could not find status by UCSB Net ID"
    
    if content_list.get("status", -1) != -1:
        return content_list["status"]
    else:
        return "Unknown Status"


def get_sep_or_term():
    # Note: The input.csv file has a header with names, input_edited does not have a header 
    with open("input.csv") as to_delete_file:
        with open("input_edited.csv", mode='w') as write_file:
            csv_reader = csv.reader(to_delete_file, delimiter=",")
            csv_writer = csv.writer(write_file, delimiter=",")

            # skip the first row
            next(csv_reader)

            for row in csv_reader: 
                ucsbNetId = row[2]

                try:
                    status = iam_get_status(ucsbNetId)

                    if status == "terminated" or status == "separated":
                        csv_writer.writerow(row)
                    else:
                        print("Status NOT terminated and NOT separated", ucsbNetId, status)

                except Exception as error:
                    print("An exception occurred:", error)
                    print("Error occurred in get_sep_or_term(). Replacing IAM access token.")
                    replace_iam_access_token()


'''
Overview:
1. Run box_export.py to loop through all box users and retrieve users with "terminated" or "separated status"
2. Run box_transfer.py to transition all files/folders from a given user to the Box Archive. These users' 
   accounts are then deleted.

Possible optimization to use getAffiliationsRemoved to only retrieve individuals who have had affiliations
removed in the last x days.
'''

if __name__ == '__main__':
    replace_iam_access_token()
    
    print('Main thread has begun.')

    public_storage_user_id = "PUBLIC_STORAGE USER ID"
    public_storage_client = client.as_user(client.user(user_id = public_storage_user_id).get())
    giant_cabinet_id = 'GIANT CABINET ID'
    read_me_file_id = "READ ME FILE ID"           # file id for the read me in the box archive account
    
    # Note: The input.csv file has a header with names, input_edited does not have a header 
    # Make sure your input.csv exists and is properly formatted before running box_transfer.py
    get_sep_or_term() 
    
    with open("input_edited.csv") as to_delete_file:
        with open("/var/tmp/csvStatusInactive.csv", mode='w') as csv_status_inactive_writer:
            with open("/var/tmp/outputLog.csv", mode='w') as output_file:
            
                csv_input = csv.reader(to_delete_file, delimiter=",")
                csv_status_inactive_writer = csv.writer(csv_status_inactive_writer, delimiter=",")
                csv_output = csv.writer(output_file, delimiter=",")
                
                csv_output.writerow(["Full Name", "UCSB Net Id", "Department", "Date of Removal"])
                
                giant_cabinet_id = create_giant_cabinet(public_storage_client, giant_cabinet_id)

                for row in csv_input: 
                    try: 
                        name = row[0]
                        email = row[1]
                        ucsbNetId = row[2]
                        box_id = row[3]
                        dataUsed = row[4]
                        department = row[5]
                        ucsbCampusId = row[6]
                        status = row[7]

                        user_to_impersonate = client.user(user_id = box_id).get() 
                        user_client = client.as_user(user_to_impersonate)
                        print(user_to_impersonate.id, user_to_impersonate.name, user_to_impersonate.login)

                        new_user_client = client.user(user_id = box_id)
                        new_user = new_user_client.get(fields = ['status'])
                        
                        date_folder_id = create_big_drawer(ucsbNetId, ucsbCampusId, giant_cabinet_id, public_storage_client)
                        
                        try: 
                            transfer_folder = user_to_impersonate.transfer_content(client.user(user_id = public_storage_user_id))
                        except:
                            # catch the 504 error, quietly handle it to let it finish transferring
                            print("Caught Error while transferring ... resuming program in 5 minutes")
                            sleep(300)

                        try:
                            move_to_date_folder(public_storage_client, transfer_folder.id, date_folder_id, read_me_file_id)
                        except: 
                            # catch the Box server side error, wait for 60 seconds, and retry the move_to_date_folder() action
                            print("Caught Box Server Side Error ... Retrying in 60 Seconds")
                            sleep(60)
                            move_to_date_folder(public_storage_client, transfer_folder.id, date_folder_id, read_me_file_id)

                        print("Account transfer successful!")
       
                        if new_user.status == "active":   
                            client.user(user_to_impersonate.id).delete()
                            print("DELETED user", ucsbNetId, "\n")
                            
                            # Set fixed offset for PST (UTC-8), ChatGPT assisted
                            pst_offset = timedelta(hours=-8)
                            utc_now = datetime.now(timezone.utc)
                            current_time_pst = utc_now + pst_offset

                            date_of_removal = str(current_time_pst.year) + "-" + str(current_time_pst.month) + "-" + str(current_time_pst.day)
                            csv_output.writerow([name, ucsbNetId, department, date_of_removal])
                        
                        else: 
                            csv_status_inactive_writer.writerow(["INACTIVE", name, email, ucsbNetId, box_id, dataUsed, department, ucsbCampusId, status])
                    
                    except Exception as error:
                        print("ERROR OCCURRED\n", error, "ERROR CAUGHT\n")
                        name = row[0]
                        email = row[1]
                        ucsbNetId = row[2]
                        box_id = row[3]
                        dataUsed = row[4]
                        department = row[5]
                        ucsbCampusId = row[6]
                        status = row[7]
                        csv_status_inactive_writer.writerow(["ERROR", name, email, ucsbNetId, box_id, dataUsed, department, ucsbCampusId, status])
                                                    
    print('Main thread done.')
   
