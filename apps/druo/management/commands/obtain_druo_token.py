from config.settings import AUTH_DRUO_URL, DRUO_URL, CLIENT_ID, CLIENT_SECRET
from django.core.management.base import BaseCommand, CommandError
from ...models import Token

import json
import os
import requests


class Command(BaseCommand):

    help = u'Go to Druo  autenticate obtain and save token'

    def handle(self, *args, **options):
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "audience": "https://druo-merchant-api.com",
            "grant_type": "client_credentials"
        } 
        headers = {
            'Content-Type': 'application/json',
            }
        response = requests.post(AUTH_DRUO_URL, data=json.dumps(data), headers=headers)
        print("la rta fue: ", response)
        result = response.json()
        print("la rta fue: ", result)
        token = Token.objects.create(
        token_type = result['token_type'],
        expires_in = result['expires_in'],
        access_token = result['access_token'],
        )


