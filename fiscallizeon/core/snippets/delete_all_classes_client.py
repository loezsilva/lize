from fiscallizeon.clients.models import Client
from fiscallizeon.classes.models import SchoolClass


CLIENT_PK = 'f1a6a4e9-7b95-4045-b6dd-f720a17a14e1'

client = Client.objects.get(pk=CLIENT_PK)
classes = SchoolClass.objects.filter(coordination__unity__client=client)

print(classes.delete())