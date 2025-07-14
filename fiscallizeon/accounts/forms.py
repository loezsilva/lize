from .models import User
from django.contrib.auth import get_user_model, login
from django import forms
from django.contrib.auth.forms import UserCreationForm

UserModel = get_user_model()


class UserCreationForm(UserCreationForm):    
    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'schools', 'how_did_you_meet_us', 'how_did_you_meet_us_form', 'accepted_terms_of_intellectual_rights_of_questions')