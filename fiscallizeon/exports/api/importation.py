from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from fiscallizeon.exports.models import Import

class ImportationErrorsAPIView(APIView):

    def get(self, request, pk=None, *args, **kwargs):
        user = self.request.user
        last_import = user.last_import
        return Response(last_import.errors if last_import and last_import.errors else [])