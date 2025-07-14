from django.contrib import admin

# Register your models here.
from fiscallizeon.candidates.models import Candidate

admin.site.register([Candidate])