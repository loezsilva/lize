from django.http.response import JsonResponse

from rest_framework.views import APIView
from rest_framework.response import Response

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.permissions import AllowAny

class CheckSincronizationIntership(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        data = request.data
        sincronizeds = []
        for _intership in data:
            intership = SchoolClass.objects.filter(
                id_erp=str(_intership['id_turma']), 
                students__id_erp=str(_intership['id_aluno']),
                coordination__in=self.request.user.get_coordinations_cache()
            ).first()
            if intership:
                sincronizeds.append(_intership)
                
        return Response(sincronizeds)
