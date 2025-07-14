from django.core.management.base import BaseCommand
from fiscallizeon.classes.models import SchoolClass

class Command(BaseCommand):
    help = 'Preenche o campo turn de todas as turmas do cliente decisão'

    def handle(self, *args, **options):
        client_id = 'a2b1158b-367a-40a4-8413-9897057c8aa2'
        schoolclasses = SchoolClass.objects.filter(coordination__unity__client__id=client_id)
        for schoolclass in schoolclasses:
            if not schoolclass.turn:
                turn_char = schoolclass.name[2:3]
                if turn_char and turn_char in ['M', 'T', 'N', 'I']:
                    cases = {
                        'M': 0,
                        'T': 1,
                        'N': 2,
                        'I': 3,
                    }
                    schoolclass.turn = cases[turn_char]
                    schoolclass.save()

        self.stdout.write(self.style.SUCCESS('Turmas preenchidas'))
