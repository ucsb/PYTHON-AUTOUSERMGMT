import requests 

def generate_iamtesttoken():
    api_url = "https://eis.identity.ucsb.edu/oauth/token"
    data = {"client_id":"CLIENTID","grant_type":"client_credentials"}
    auth = ("CLIENTID","CLIENTCREDS")
    req=requests.post(api_url, data=data, auth=auth)
    iamtesttoken = req.json()["access_token"]
    return iamtesttoken
