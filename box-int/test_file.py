# All import statements that will be used in box_export.py and/or box_transfer.py
from boxsdk import BoxAPIException, JWTAuth, Client                                 # Box API
from boxsdk.object.metadata_template import MetadataField, MetadataFieldType
from boxsdk.object.search import MetadataSearchFilter, MetadataSearchFilters
import requests                                                                     # test environments require VPN to access 
from datetime import datetime, timedelta, timezone         
from datetime import date               
from time import sleep
from threading import Thread
import csv 
import logging 
import sys 
import secret_credentials
from secret_credentials import generate_iamtesttoken
import os 


url_base = 'https://eis.identity.ucsb.edu/.' 
iam_headers = { "Authorization" : 'Bearer {}'.format(secret_credentials.generate_iamtesttoken()) }

box_config = JWTAuth.from_settings_file('PROD_config.json') 
client = Client(box_config)
service_account = client.user().get()
print(f'Service Account user ID is {service_account.id}')


def iam_get_status(ucsbNetId):
    # Concatenate base URL and request URL
    request_url = "{}/people/readonly/{}/status".format(url_base, ucsbNetId)
    response = requests.get(request_url, headers=iam_headers)
    content_list = response.json()
    
    if content_list.get("status", -1) != -1:
        return content_list["status"]
    else:
        return "Unknown Status"


def iam_get_campus_id(ucsbNetId):
    # Concatenate base URL and request URL
    request_url = "{}/people/readonly/{}".format(url_base, ucsbNetId)
    response = requests.get(request_url, headers=iam_headers)
    content_list = response.json()
    
    if content_list.get("ucsbCampusId", -1) != -1:
        return content_list["ucsbCampusId"]
    else:
        return "Unknown UCSB Campus ID"


if __name__ == '__main__':
    public_storage_user_id = "PUBLIC STORAGE USER ID"
    public_storage_client = client.as_user(client.user(user_id = public_storage_user_id).get())
    giant_cabinet_id = 'GIANT CABINER ID'
    read_me_file_id = "READ ME FILE ID"           
    box_id = "USER BOX ID"
    ucsbNetId = "USER NET ID"

    user_to_impersonate = client.user(user_id = box_id).get() 
    user_client = client.as_user(user_to_impersonate)
    print(user_to_impersonate.id, user_to_impersonate.name, user_to_impersonate.login)

    new_user_client = client.user(user_id = box_id)
    new_user = new_user_client.get(fields = ['status'])
    print(f"Box Status: {new_user.status}")

    status = iam_get_status(ucsbNetId)
    print(f"UCSB Identity API Status: {status}")

    ucsbCampusId = iam_get_campus_id(ucsbNetId)
    print(f"UCSB Campus ID: {ucsbCampusId}")

    new_user_client = client.user(user_id = box_id)
    new_user = new_user_client.get(fields = ['id','name','enterprise'])
    print(f"Enterprise: {new_user.enterprise}")
    
    print("Testing CSV read and write!")
    with open("test_input.csv", mode='r') as csv_file:
        with open("/var/tmp/test_write.csv", mode='w') as write_file:
        # with open("test_write.csv", mode='w') as write_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            csv_writer = csv.writer(write_file, delimiter=',')

            for row in csv_reader:
                csv_writer.writerow(row)
                print(row)
                
    print("End of CSV read and write")

    # Set fixed offset for PST (UTC-8), ChatGPT assisted
    pst_offset = timedelta(hours=-8)
    utc_now = datetime.now(timezone.utc)
    current_time_pst = utc_now + pst_offset
    print("Current time in PST:", current_time_pst)

    print(current_time_pst.year, current_time_pst.month, current_time_pst.day)
