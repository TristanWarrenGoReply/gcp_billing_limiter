import os
import requests

# Install Google Libraries
from google.cloud import secretmanager

# Setup the Secret manager Client
# client = secretmanager.SecretManagerServiceClient()
# Get the sites environment credentials
project_id = os.environ["PROJECT_NAME"]

# Request Header
headers = {
    'Content-Type': 'application/json'
}

def billing_limiter(data, context):

    budget_data = data

    budget       = budget_data['budgetAmount']
    cost         = budget_data['costAmount']
    threshold    = budget_data.get('alertThresholdExceeded', 0)
    billingPeriod = budget_data['costIntervalStart']
    currency     = budget_data['currencyCode']

    print("""Handling budget notification for project id: {}
             The budget is set to: {}
             The cost for this billing period is: {}
             The threshold for this alert is: {}%
             For the billing period: {}
    """.format(project_id, budget, cost, threshold*100, billingPeriod))

    # If the billing is already disabled, stop Cloud Function execution
    if not __is_billing_enabled(project_id):
        raise RuntimeError('Billing already in disabled state')
    else:
        # Disable or not the billing for the project id depending on the total and the budget
        if threshold < 1:
            print('No action will be taken on the total amount of {} {} for the period {}.'
                        .format(cost, currency, billingPeriod))
        else:
            print('The monthly cost is more than {} {} for period {}, the billing will be disabled for project id {}.'
                        .format(budget, currency, billingPeriod, project_id))

            __disable_billing_for_project(project_id)
            # print("BILLING DISABLED") # For testing
            
def __is_billing_enabled(project_id):
    service = __get_cloud_billing_service()
    billing_info = service.projects().getBillingInfo(name='projects/{}'.format(project_id)).execute()
    
    if not billing_info or 'billingEnabled' not in billing_info:
        return False
    return billing_info['billingEnabled']

def __get_cloud_billing_service():
    # Creating credentials to be used for authentication, by using the Application Default Credentials
    # The credentials are created  for cloud-billing scope
    from oauth2client.client import GoogleCredentials
    credentials = GoogleCredentials.get_application_default()

    # The name and the version of the API to use can be found here https://developers.google.com/api-client-library/python/apis/
    from apiclient import discovery
    return discovery.build('cloudbilling', 'v1', credentials=credentials, cache_discovery=False)

def __disable_billing_for_project(project_id):
    service = __get_cloud_billing_service()
    billing_info = service.projects()\
        .updateBillingInfo(name='projects/{}'.format(project_id), body={'billingAccountName': ''}).execute()
    assert 'billingAccountName' not in billing_info