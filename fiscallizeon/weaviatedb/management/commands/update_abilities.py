from datetime import datetime

import weaviate
from weaviate.exceptions import ObjectAlreadyExistsException, UnexpectedStatusCodeException

from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.bncc.models import Abiliity
from fiscallizeon.weaviatedb.classes.abilities import abilities_definition

class Command(BaseCommand):
    help = 'Exporta habilidades BNCC para Weaviate'
    
    def __init__(self, *args, **kwargs):
        self.weaviate_class_name = 'Abilities'
        self.client = weaviate.Client(
            url = settings.WEAVIATE_URL, 
            additional_headers = {
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )
        return super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('--start_date', type=str, help='Data da última modificação no formato YYYY-MM-DD')
        parser.add_argument('--rebuild', action='store_true', default=False, help='Importa todas as habilidades do zero (apaga o schema atual!)')

    def create_schema(self):
        try:
            self.client.schema.delete_class(abilities_definition['class'])
            self.client.schema.create_class(abilities_definition)
            print("Schema criado")
        except UnexpectedStatusCodeException:
            self.client.schema.update_config(abilities_definition['class'], abilities_definition)
            print("Schema atualizado")

    def create_update_abilities(self, abilities):
        for ability in abilities:
            data_object={
                "code": ability.code,
                "text": ability.text,
                "client": str(ability.client_id) if ability.client_id else None,
                "subject": str(ability.subject_id) if ability.subject else None,
                "knowledge_area": str(ability.knowledge_area_id) if ability.knowledge_area else None,
                "grades": [str(a) for a in ability.grades.all().values_list('pk', flat=True)],
            }

            try:
                self.client.data_object.create(
                    class_name=self.weaviate_class_name,
                    uuid=ability.id,
                    data_object=data_object
                )
                print(f"Habilidade {ability.code} (cliente: {ability.client_id}) criada com sucesso")
            except ObjectAlreadyExistsException:
                self.client.data_object.update(
                    class_name=self.weaviate_class_name,
                    uuid=ability.id,
                    data_object=data_object
                )
                print(f"Habilidade {ability.code} (cliente: {ability.client_id}) atualizada com sucesso")

    def bulk_create_abilities(self, abilities):
        self.client.batch.configure(batch_size=100, num_workers=2)
        with self.client.batch as batch:
            for ability in abilities:
                batch.add_data_object(
                    {
                        "code": ability.code,
                        "text": ability.text,
                        "client": str(ability.client_id) if ability.client_id else None,
                        "subject": str(ability.subject_id) if ability.subject else None,
                        "knowledge_area": str(ability.knowledge_area_id) if ability.knowledge_area else None,
                        "grades": [str(a) for a in ability.grades.all().values_list('pk', flat=True)],
                    },
                    self.weaviate_class_name,
                    uuid=ability.id,
                )
        
        print(f"Importação concluída! {abilities.count()} habilidades importadas")


    def handle(self, *args, **kwargs):
        date = datetime.now().date()

        if start_date := kwargs.get('start_date', None):
            try:
                date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Formato de data inválido. Use YYYY-MM-DD.'))
                return

        if kwargs.get('rebuild', False):
            self.create_schema()
            abilities = Abiliity.objects.all()
            self.bulk_create_abilities(abilities)
        else:
            abilities = Abiliity.objects.filter(updated_at__date__gte=date)
            self.create_update_abilities(abilities)
