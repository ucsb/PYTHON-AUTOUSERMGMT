import requests                                                                 # test environments require VPN to access 
from datetime import date                                                       # comparing the "cutoff" date to affiliation_removed_date
import csv                                                                      # reading / writing to the CSV files  
import secret_credentials                                                       # file containing secrets


url_base = 'https://eis.identity.ucsb.edu/.' 
iam_headers = { "Authorization" : 'Bearer {}'.format(secret_credentials.generate_iamtesttoken()) }


def replace_iam_access_token():
    # generate a new access token
    global iam_headers
    iamtesttoken = secret_credentials.generate_iamtesttoken()
    iam_headers = { "Authorization" : 'Bearer {}'.format(iamtesttoken) }
    print("new access token created (inside replace_iam_access_token)", iamtesttoken)


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
    
    # Speed up affiliations request with json + dictionary instead of parsing through strings
    if content_list.get("status", -1) != -1:
        return content_list["status"]
    else:
        return "Unknown Status"


def get_campus_id(ucsbNetId):
    request_url = "{}/people/readonly/{}".format(url_base, ucsbNetId)
    response = requests.get(request_url, headers=iam_headers)

    campus_id = ""
    try:
        campus_id = response.json()[("ucsbCampusId")]
    except:
        campus_id = "Unknown Campus ID"

    return campus_id


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


if __name__ == '__main__':
    replace_iam_access_token()
    
    print('Main thread has begun.')

    # Note: The input.csv file has a header with names, input_edited does not have a header 
    # get_sep_or_term() # ADD THIS BACK FOR CHECKING STATUS with ORIGINAL FILE being input.csv

    # Add your user net ids here in string format ex: ["joegaucho","joebruin"]
    users =  []
    for user in users:
        print(iam_get_status(user) + " " + get_campus_id(user))    

    print('Main thread done.')
   