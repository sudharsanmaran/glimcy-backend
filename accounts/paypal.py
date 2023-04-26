import requests
from django.conf import settings


class PayPalAPI:
    PAYPAL_BASE_URL = settings.PAYPAL_BASE_URL
    PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
    PAYPAL_CLIENT_SECRET = settings.PAYPAL_CLIENT_SECRET

    def __init__(self):
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        url = f'{self.PAYPAL_BASE_URL}/v1/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'client_credentials'}
        auth = (self.PAYPAL_CLIENT_ID, self.PAYPAL_CLIENT_SECRET)

        response = requests.post(url, headers=headers, data=data, auth=auth)
        response.raise_for_status()

        return response.json()['access_token']

    def get_billing_plans(self):
        url = f'{self.PAYPAL_BASE_URL}/v1/billing/plans'
        headers = {'Authorization': f'Bearer {self.access_token}'}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_detail_billing_plan(self, plan_id):
        url = f'{self.PAYPAL_BASE_URL}/v1/billing/plans/{plan_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Error retrieving plan {plan_id}: {response.json()}')

    def get_subscription(self, subscription_id: str):
        url = f'{self.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-PAYPAL-SECURITY-CONTEXT': f'{{"clientId": "{self.PAYPAL_CLIENT_SECRET}"}}',
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def cancel_subscription(self, subscription_id: str, reason: str):
        url = f'{self.PAYPAL_BASE_URL}/v1/billing/subscriptions/{subscription_id}/cancel'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-PAYPAL-SECURITY-CONTEXT': f'{{"clientId": "{self.PAYPAL_CLIENT_SECRET}"}}',
        }
        data = {'reason': reason}

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        return {'message': 'Subscription cancelled successfully'}
