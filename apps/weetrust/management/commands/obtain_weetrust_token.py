from ...models import AccessTokenWeetrust

from django.core.management.base import BaseCommand, CommandError

from config.settings import WEETRUST_URL, WEETRUST_USER_ID, WEETRUST_API_KEY

import requests
import json

class Command(BaseCommand):

    help = u'Connect to WeTrust autenticate and Save token (token expires at 5 minutes)'

    def handle(self, *args, **options):
        headers = {
            'user-id': WEETRUST_USER_ID,
            'api-key': WEETRUST_API_KEY
            }
        data = {}
        url_obtain_token = WEETRUST_URL+'access/token/'
        
        response = requests.post(url_obtain_token, data=json.dumps(data), headers=headers)
        result = response.json()
        token = AccessTokenWeetrust.objects.create(
            value = result['responseData']['accessToken']
        )
        return