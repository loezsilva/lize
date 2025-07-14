"""
Cria um número de fiscais baseado no id do cliente e adiciona a todas as coordenações
"""

from fiscallizeon.clients.models import Client, SchoolCoordination
from fiscallizeon.inspectors.models import Inspector

#CLIENT_PK = 'ca7c4dd5-c327-4b99-b991-cbf749ff880e' #Dom Bosco
#CLIENT_PK = '4d5ad010-fa80-4359-ac82-99faebc3519a' #São José
CLIENT_PK = 'c1e071a4-d0c0-48f5-a820-8a0c9e914c33'

SUFFIX = 'marista.fiscal.com.br'
QUANTITY = 30

client = Client.objects.get(pk=CLIENT_PK)
coordinations = SchoolCoordination.objects.filter(unity__client=client)

for i in range(1, QUANTITY+1):
    inspector = Inspector.objects.create(
        name=f'Fiscal {i}',
        email=f'fiscal{i}@{SUFFIX}',
        inspector_type=Inspector.INSPECTOR,
    )

    for coordination in coordinations:
        inspector.coordinations.add(coordination)

    print("Criado", inspector)