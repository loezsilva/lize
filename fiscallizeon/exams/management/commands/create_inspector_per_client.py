from django.core.management.base import BaseCommand
from fiscallizeon.exams.models import TeacherSubject
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.clients.models import Client, SchoolCoordination
from django.db.models import Q

class Command(BaseCommand):
    help = 'Cria um "professor" por cliente relacionado a todas as disciplinas (TeacherSubject) daquele cliente.'

    def handle(self, *args, **kwargs):
        clients = Client.objects.all()

        for client in clients:
            subjects = Subject.objects.filter(
                Q(parent_subject__isnull=True) |
                Q(client__isnull=True) |
                Q(
                    Q(parent_subject__isnull=False) &
                    Q(client=client)
                )
            )
            if client.use_only_own_subjects:
                subjects =  Subject.objects.filter(
                    client=client
                ).distinct()             
            

            professor, created = Inspector.objects.get_or_create(
                email=f"professor_ia_{client.id}@fiscallize.com.br",
                defaults={
                    'name': f"Professor IA {client.name[:35]}",
                    'is_inspector_ia': True,
                    'inspector_type': Inspector.TEACHER,
                }
            )
       
            for subject in subjects:
                TeacherSubject.objects.get_or_create(
                    teacher=professor,
                    subject=subject,
                    defaults={
                        'school_year': 2024,
                        'active': True
                    }
                )
 
            coordinations = SchoolCoordination.objects.filter(unity__client=client)

            for coordination in coordinations:
                professor.coordinations.add(coordination)

        self.stdout.write(self.style.SUCCESS('Professores criados com sucesso para todos os clientes.'))

