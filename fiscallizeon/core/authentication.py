from django.utils import timezone
from fiscallizeon.accounts.models import User 
from fiscallizeon.applications.models import HashAccess 
from rest_framework import authentication 
from rest_framework import exceptions 

class ParentAuthentication(authentication.BaseAuthentication): 
    def authenticate(self, request):                  
        hash = request.META.get('HTTP_HASH', None)
        if not hash: 
            return None 
        try:             
            hash = HashAccess.objects.get(pk=hash)             
            user = hash.application_student.student.user
            if hash.validity < timezone.localtime(timezone.now()).date():
                raise HashAccess.DoesNotExist
        except HashAccess.DoesNotExist: 
            raise exceptions.AuthenticationFailed('Erro de autenticação ou prazo de acesso expirado') 
        return (user, None)
