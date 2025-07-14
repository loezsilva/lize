import requests
from mixer.backend.django import mixer
from fiscallizeon.accounts.models import User
from fiscallizeon.core.utils import CustomTransactionTestCase
from fiscallizeon.accounts.models import User
from fiscallizeon.core.utils import get_all_named_patterns, get_reversible_url
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token
import csv
import os
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class TestUrlsManager(StaticLiveServerTestCase, CustomTransactionTestCase):
    databases = '__all__'
    
    def setUp(self):
        username = get_random_string(16)
        password = get_random_string(16)
        self.user = mixer.blend(User, username=username)
        self.user.set_password(password)
        token = Token.objects.create(user=self.user)
        self.user.save()
        self.token = token.key
    
    def test_urls(self):
        routers_without_errors = []
        routers_with_errors = []
        named_patterns = get_all_named_patterns()
        
        def get_title(html_text): 
            import re
            match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                return title
            return ''
        
        for name, pattern_str in named_patterns:
            
            path = get_reversible_url(name, pattern_str)
            
            if not path:
                print(f"ignorando rota '{name}': não foi possível reverter.")
                continue
            
            response = requests.get(self.live_server_url + path)
            # response = requests.get('http://0.0.0.0:8000' + path, headers={'Authorization': f'Token {self.token}'})
            
            error_object = {
                'router': path,
                'status': response.status_code,
                'text': get_title(response.text),
            }

            if response.status_code >= 500:
                routers_with_errors.append(error_object)
            else:
                routers_without_errors.append(error_object)                
                
        # if routers_with_errors:
        #     os.makedirs("tmp", exist_ok=True)
        #     with open("tmp/errors.csv", "w", newline="", encoding="utf-8") as csvfile:
        #         writer = csv.DictWriter(csvfile, fieldnames=["router", "status", "text"])
        #         writer.writeheader()
        #         writer.writerows(routers_with_errors)
                
        #     with open("tmp/success.csv", "w", newline="", encoding="utf-8") as csvfile:
        #         writer = csv.DictWriter(csvfile, fieldnames=["router", "status", "text"])
        #         writer.writeheader()
        #         writer.writerows(routers_without_errors)
        
        self.assertEqual(len(routers_with_errors), 0, msg=list(map(lambda x: x['router'], routers_with_errors)))