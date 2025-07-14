from django.conf import settings

from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from fiscallizeon.materials.models import FavoriteStudyMaterial, StudyMaterial

from fiscallizeon.students.models import Student
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication 



class FavoriteStudyMaterialAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.STUDENT]
    authentication_classes = [CsrfExemptSessionAuthentication, ]

    def post(self, request, pk):

        favorite, created = FavoriteStudyMaterial.objects.get_or_create(study_material=StudyMaterial.objects.get(pk=pk), student=self.request.user.student)
        if created:
            favorite.save()
            return Response({"id": pk, "status": "success", 'removed': False, "message": "Material favoritado com sucesso!"})
        else:
            favorite.delete()
            return Response({"id": pk, "status": "success", 'removed': True, "message": "Material removido da lista de favoritos!"})

favorite_study_material = FavoriteStudyMaterialAPIView.as_view()