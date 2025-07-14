from requests import Response
from rest_framework import status

def get_bncc(bncc_pk):
    from fiscallizeon.bncc.models import Abiliity, Competence
    from fiscallizeon.subjects.models import Topic

    if not bncc_pk:
        return
    try:
        ability = Abiliity.objects.get(pk=bncc_pk)
        return ability
    except:
        pass
    try:
        competence = Competence.objects.get(pk=bncc_pk)
        return competence
    except:
        pass
    try:
        topic = Topic.objects.get(pk=bncc_pk)
        return topic
    except:
        pass
    
    return None