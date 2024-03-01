# Automated Box User Management Python Program

# Project Description
The Box User Management Python program automatically handles the offboarding process for UCSB Box users using a three-step process. First, the box_export.py program identifies all users in the UCSB Box Enterprise environment that have been marked as "terminated" or "separated" by the UCSB Identity API. We refer to these users as unaffiliated users. Second, the box_transfer.py program transfers the data stored in each unaffiliated user's Box account to the Box Archive, a holding storage account. The Box Archive contains a folder in the root directory named "Giant Cabinet." The Giant Cabinet holds unique user drawers containing a date folder with the user's owned files and folders. The folder structure of the Box Archive account looks like Giant Cabinet -> User Drawers -> Date Folder -> Unaffiliated User's Files & Folders. Finally, the program deletes the user's account from the UCSB enterprise.

# Box Transfer Python Program Requirements: 
- Install Python 3.9.6
- Install boxsdk using: pip install boxsdk
- Install JWT dependencies using: pip install "boxsdk[jwt]" 
- Make sure there is a JSON file called PROD_config.json containing the clientID, clientSecret, publicKey, private key, passphrase, and enterpriseID in the same directory as box_export.py and box_transfer.py

# Required Python Libraries:

| Package           | Version |
| ------------- | ------------- |
| requests          | ~=2.31.0 |
| boxsdk            | ~=3.9.2  |
| boxsdk[jwt]       | ~=3.9.2  |
       
# How to create a Box user export on Jenkins: 
- Uncomment the line (remove the //), sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_export.py' in the Jenkinsfile
- Comment the line (add the //), // sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_transfer.py'
- This is so that only the box_export.py program is run
- Run the following commands in the terminal: git add Jenkinsfile, git commit -m "your message here", git push origin develop
- After Jenkins finishes running, the CSV file /var/tmp/box_export.csv can be found as an artifact in the Jenkins workspace
- Open the /var/tmp/box_export.csv in Excel and click on the "Data Used" column header to sort the entries in the data used column in ascending order
- Click on the "Full Name" column header to sort the names in lexicographically ascending order 
- As a result, we now have a full Box user export in order from the least space used to the greatest space used
- Make sure that the Box ID column is formatted as Text. Right-click the column header and select "Format Cells" 
- On the popup menu, choose "Text" and click "OK" 
- Double-check that there are no leading spaces or trailing spaces in front of the data entries
- Add input.csv to your local directory. This export file will be used as the input.csv in the next step

# How to start the Box transfer on Jenkins: 
- Comment the line (add the //), // sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_export.py' in the Jenkinsfile
- Uncomment the line (remove the //), sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_transfer.py'
- This is so that only the box_transfer.py program is run
- Prepare an input.csv file with the first row containing: Full Name,Email,UCSB Net Id,Box Id,Data Used,Department,Status
- Each subsequent row is an entry such as Joe,joe@ucsb.edu,joe,123456,123,MATH,separated
- See the previous block for more information about how to create the input.csv file
- Run the following commands in the terminal: git add Jenkinsfile, git add input.csv, git commit -m "your message here", git push origin develop
- Running the above command will create 2 CSV artifacts in Jenkins: csvStatusInactive.csv and outputLog.csv. Artifacts will only show in the Jenkins dashboard for successful builds
- The csvStatusInactive file contains all the users who return inactive when checking the IAM user status and users who coincided with an error (an error was thrown while the user was being processed) 
- The outputLog.csv contains all the users who have been affected by the Box Transfer program with the information: Full Name, UCSB Net Id, Department, and Date of Removal
