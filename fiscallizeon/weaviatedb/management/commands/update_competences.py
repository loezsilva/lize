from datetime import datetime

import weaviate
from weaviate.exceptions import ObjectAlreadyExistsException, UnexpectedStatusCodeException

from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.bncc.models import Competence
from fiscallizeon.weaviatedb.classes.competences import competences_definition

class Command(BaseCommand):
    help = 'Exporta competências BNCC para Weaviate'
    
    def __init__(self, *args, **kwargs):
        self.weaviate_class_name = 'Competences'
        self.client = weaviate.Client(
            url = settings.WEAVIATE_URL, 
            additional_headers = {
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )
        return super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('--start_date', type=str, help='Data da última modificação no formato YYYY-MM-DD')
        parser.add_argument('--rebuild', action='store_true', default=False, help='Importa todas as competências do zero (apaga o schema atual!)')

    def create_schema(self):
        try:
            self.client.schema.delete_class(competences_definition['class'])
            self.client.schema.create_class(competences_definition)
            print("Schema criado")
        except UnexpectedStatusCodeException:
            self.client.schema.update_config(competences_definition['class'], competences_definition)
            print("Schema atualizado")

    def create_update_competences(self, competences):
        for competence in competences:
            data_object={
                "code": competence.code,
                "text": competence.text,
                "client": str(competence.client_id) if competence.client_id else None,
                "subject": str(competence.subject_id) if competence.subject else None,
                "knowledge_area": str(competence.knowledge_area_id) if competence.knowledge_area else None,
            }
            try:
                self.client.data_object.create(
                    class_name=self.weaviate_class_name,
                    uuid=competence.id,
                    data_object=data_object,
                )
                print(f"Competência {competence.code} (cliente: {competence.client_id}) criada com sucesso")
            except ObjectAlreadyExistsException:
                self.client.data_object.update(
                    class_name=self.weaviate_class_name,
                    uuid=competence.id,
                    data_object=data_object,
                )
                print(f"Competência {competence.code} (cliente: {competence.client_id}) atualizada com sucesso")
    
    def bulk_create_competences(self, competences):
        self.client.batch.configure(batch_size=100, num_workers=2)
        with self.client.batch as batch:
            for competence in competences:
                batch.add_data_object(
                    {
                        "code": competence.code,
                        "text": competence.text,
                        "client": str(competence.client_id) if competence.client_id else None,
                        "subject": str(competence.subject_id) if competence.subject else None,
                        "knowledge_area": str(competence.knowledge_area_id) if competence.knowledge_area else None,
                    },
                    self.weaviate_class_name,
                    uuid=competence.id,
                )
        
        print(f"Importação concluída! {competences.count()} competências importadas")

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
            competences = Competence.objects.all()
            self.bulk_create_competences(competences)
        else:
            competences = Competence.objects.filter(updated_at__date__gte=date)
            self.create_update_competences(competences)
