
import sys

from PIL import Image
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_framework import serializers
from fiscallizeon.answers.models import Attachments

class AttachmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachments
        fields = '__all__'