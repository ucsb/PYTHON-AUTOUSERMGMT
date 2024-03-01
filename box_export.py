from boxsdk import JWTAuth, Client      # Box API
import requests                         # test environments require VPN to access 
from datetime import date               # For comparing the "cutoff" date to affiliation_removed_date
from time import sleep                  # For regenerating the access token
from threading import Thread            # For regenerating the access token
import csv                              # For writing a CSV file containing separated / terminated users
import secret_credentials               # For generating the iamtesttoken


url_base = 'https://eis.identity.ucsb.edu/.' 
iam_headers = { "Authorization" : 'Bearer {}'.format(secret_credentials.generate_iamtesttoken()) }

box_config = JWTAuth.from_settings_file('PROD_config.json') 
client = Client(box_config)
service_account = client.user().get()
print(f'Service Account user ID is {service_account.id}')


def replace_iam_access_token():
    # generate a new access token
    global iam_headers

    # run forever
    while True:
        iamtesttoken = secret_credentials.generate_iamtesttoken()
        iam_headers = { "Authorization" : 'Bearer {}'.format(iamtesttoken) }
        print("new access token created (inside replace_iam_access_token)", iamtesttoken)

        # Block for 29 min (60 seconds * 29 min)
        sleep(60 * 29) 


def get_affiliations_removed_users(dateFilter, cutoff_date):
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


if __name__ == '__main__':
    print('Starting background access token generation...')
    daemon = Thread(target = replace_iam_access_token, daemon=True, name="Access Token Generator:")
    daemon.start()

    print('Main thread has begun.')

    # Export all box users
    with open("/var/tmp/box_export.csv", mode='w') as write_file:
        csv_writer = csv.writer(write_file, delimiter=",")
        csv_writer.writerow(["Full Name", "Email", "UCSB Net Id", "Box Id", "Data Used", "Department", "Status"])
        
        # To analyze a subsection of users, use the get_affiliations_removed_users function all instead of 
        # looping through all useres in Box

        '''
        example:
        data_dict = get_affiliations_removed(start_date, end_date)
        if netId in data_dict:
            if data_dict[netId]["terminated"]:  
                handle unaffiliated users      
        '''

        users = client.users(user_type='all')

        for user in users:
            email=f'{user.login}'
            netIdTemp=email.split("@")
            netId=str(netIdTemp[0])
            box_id = user.id
            name = user.name
            data_used = user.space_used

            # Get the user's status from the UCSB Identity API
            request_url = "{}/people/readonly/{}/status".format(url_base, netId)
            response = requests.get(request_url, headers=iam_headers)

            status = ""
            try:
                status = response.json()["status"]
            except: 
                status = "Unknown Status"
            
            # Get the user's UCSB Campus ID and Department (only readonly calls are in scope
            # other calls lead to insufficient scope)
            request_url = "{}/people/readonly/{}".format(url_base, netId)
            response = requests.get(request_url, headers=iam_headers)
            
            campus_id = ""
            try:
                campus_id = response.json()[("ucsbCampusId")]
            except:
                campus_id = "Unknown Campus ID"

            department = ""
            try:
                department = response.json()["ucsbHomeDepartment"]
            except:
                department = "Unknown Department"

            if status == "terminated" or status == "separated":
                print(f"{name}, {email}, {netId}, {box_id}, {data_used}, {department}, {campus_id}, {status}")
                csv_writer.writerow([name, email, netId, box_id, data_used, department, campus_id, status])

    print('Main thread done.')