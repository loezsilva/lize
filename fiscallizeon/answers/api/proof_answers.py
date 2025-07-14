import logging
from rest_framework import generics
from fiscallizeon.answers.models import ProofAnswer

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend 

from fiscallizeon.answers.serializers.proof_answers import ProofAnswerSimpleSerializer

logger = logging.getLogger()

class ProofAnswerListAPIView(generics.ListAPIView):
    model = ProofAnswer
    serializer_class = ProofAnswerSimpleSerializer
    queryset = ProofAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        queryset = queryset.filter(application_student__student__client__in=self.request.user.get_clients_cache())
        
        if self.request.GET.get('code'):
            queryset = queryset.filter(code__icontains=self.request.GET.get('code'))
        
        return queryset[:10]