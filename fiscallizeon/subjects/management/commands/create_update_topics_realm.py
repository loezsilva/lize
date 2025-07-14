from django.core.management.base import BaseCommand
from fiscallizeon.integrations.models import SubjectCode
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.bncc.models import Abiliity, Competence

class Command(BaseCommand):
    help = 'Cria/Atualiza assuntos na plataforma Realm ip.tv da SEDUC-SP'

    CLIENT_ID = '83579d53-7d1c-477d-aafc-09c3070bdb41'

    def handle(self, *args, **kwargs):
        topics = Topic.objects.filter(
            client=self.CLIENT_ID,
        )

        print(topics.count())
