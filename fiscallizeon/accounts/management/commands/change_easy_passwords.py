import sys
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from fiscallizeon.accounts.models import User

class Command(BaseCommand):
    help = 'Altera a senhad os usuários para uma senha mais forte'

    def create_and_print_new_password(self, user: User, old_password):
        new_password = get_random_string(16, allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        print(f"{user.username if user.username else user.email},{old_password},{new_password}")
        user.set_password(new_password)
        user.save()
        
    def handle(self, *args, **kwargs):
        common_passwords = [
            'fiscallize2021',
            'fiscallize2022',
            'fiscallize2023',
            'lize2021',
            'lize2022',
            'lize2023',
            '123qwe123!',
            '123qwe123@',
        ]
        
        print(f"usuario,senha,nova senha")
        users = User.objects.filter(is_active=True, last_login__isnull=False)
        for user in users:
            if(user.check_password(user.email)):
                self.create_and_print_new_password(user, user.email)
                continue
            for password in common_passwords:
                if(user.check_password(password)):
                    self.create_and_print_new_password(user, password)
                    continue