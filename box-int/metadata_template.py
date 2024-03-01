from boxsdk import BoxAPIException, JWTAuth, Client      # Box API
from boxsdk.object.metadata_template import MetadataField, MetadataFieldType
from boxsdk.object.search import MetadataSearchFilter, MetadataSearchFilters
import secret_credentials                               # For generating the iamtesttoken


url_base = 'https://eis.identity.ucsb.edu/.' 
headers = { "Authorization" : 'Bearer {}'.format(secret_credentials.generate_iamtesttoken()) }

config = JWTAuth.from_settings_file('PROD_config.json') 
client = Client(config)
service_account = client.user().get()
print(f'Service Account user ID is {service_account.id}')

print("Attempting to create metadata template")

try:
    templates = client.get_metadata_templates()
    for template in templates:
        print(f'Metadata template {template.templateKey} is in enterprise scope')

    fields = [
        MetadataField(MetadataFieldType.STRING, 'drawer_name'),
    ]

    template = client.create_metadata_template('FolderMetadata', fields, hidden=False)
    print(f'Metadata template ID {template.scope}/{template.templateKey} created!')

except:
    print("Unable to create Metadata template (may already exist)")
