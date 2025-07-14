from rest_framework import status
from rest_framework.response import Response

def handle_question_duplication():
    return Response(f"A questão já foi adicionada a este caderno, não é possível adicionar novamente", status=status.HTTP_401_UNAUTHORIZED)