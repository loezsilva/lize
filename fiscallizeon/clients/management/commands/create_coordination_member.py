from django.core.management.base import BaseCommand

from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client, SchoolCoordination, CoordinationMember

class Command(BaseCommand):
    help = 'Cadastra coordination member a todas as coordenações'

    #CLIENT_PK = '4d5ad010-fa80-4359-ac82-99faebc3519a' #São José
    #CLIENT_PK = 'ca7c4dd5-c327-4b99-b991-cbf749ff880e' #Dom Bosco
    CLIENT_PK = 'c1e071a4-d0c0-48f5-a820-8a0c9e914c33'

    PEOPLE = [
        {'name': 'Maristela Bezerra de Melo Freire', 'email': 'mfreire@marista.edu.br'},
        {'name': 'Pabllo Fabiano Gomes Cruz', 'email': 'pcruz.rn@marista.edu.br'}
    ]
       

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=self.CLIENT_PK)
        coordinations = SchoolCoordination.objects.filter(unity__client=client)

        for person in self.PEOPLE:
            user = User.objects.filter(username=person['email']).first()
            
            if not user:
                user = User.objects.create_user(
                    name=person['name'],
                    email=person['email'],
                    username=person['email'],
                    password=person['email'],
                )

            for coordination in coordinations:
                coordination_member, _ = CoordinationMember.objects.get_or_create(
                    coordination=coordination,
                    user=user,
                )

            print("Criado usuário", user)