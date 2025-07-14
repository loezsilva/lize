from django.contrib import admin
from .models import FavoriteStudyMaterial, StudyMaterial
# Register your models here.
admin.site.register([StudyMaterial, FavoriteStudyMaterial])