from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import (
    ValidationError,
)
from django.utils.translation import gettext as _

class CustomCommonPasswordValidator(CommonPasswordValidator):
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
    
    def validate(self, password, user=None):
        self.passwords = self.passwords.union(self.common_passwords)
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                _("This password is too common."),
                code="password_too_common",
            )