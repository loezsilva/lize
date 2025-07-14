from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from fiscallizeon.ai.openai.search_ai import search

class SuperSearchAPIView(APIView):
    
    def get(self, request, pk=None):
        term = request.GET.get('term')
        user = self.request.user
        return Response(search(user, term))