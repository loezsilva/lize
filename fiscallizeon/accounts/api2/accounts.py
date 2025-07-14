from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db.models import Q
from django.conf import settings

from fiscallizeon.accounts.models import User
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class UsersViewSet(viewsets.GenericViewSet):
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    permission_classes = [CheckHasPermissionAPI]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    @action(detail=False, methods=['PATCH'])
    def accept_terms_question_import(self, request, pk=None):
        user: User = self.request.user
        user.accept_terms_of_question_import = True
        user.save()
        
        return Response()
    
    @action(detail=False, methods=['POST'])
    def inspector_email_already_exists(self, request, pk=None):
        email = request.data.get('email')
        exist = Inspector.objects.filter(
            Q(email=email) |
            Q(user__email=email)
        ).exists()
        
        return Response({'email_already_exists': exist})