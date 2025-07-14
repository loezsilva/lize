from datetime import datetime

import weaviate
from weaviate.exceptions import ObjectAlreadyExistsException, UnexpectedStatusCodeException

from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.subjects.models import Topic
from fiscallizeon.weaviatedb.classes.topics import topics_definition

class Command(BaseCommand):
    help = 'Exporta assuntos para Weaviate'
    
    def __init__(self, *args, **kwargs):
        self.weaviate_class_name = topics_definition['class']
        self.client = weaviate.Client(
            url = settings.WEAVIATE_URL, 
            additional_headers = {
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )
        return super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('--start_date', type=str, help='Data da última modificação no formato YYYY-MM-DD')
        parser.add_argument('--rebuild', action='store_true', default=False, help='Importa todos os assuntos do zero (apaga o schema atual!)')

    def create_schema(self):
        try:
            self.client.schema.delete_class(topics_definition['class'])
            self.client.schema.create_class(topics_definition)
            print("Schema criado")
        except UnexpectedStatusCodeException:
            self.client.schema.update_config(topics_definition['class'], topics_definition)
            print("Schema atualizado")

    def create_update_topics(self, topics):
        for topic in topics:
            data_object={
                "name": topic.name,
                "subject": str(topic.subject_id),
                "client": str(topic.client_id) if topic.client_id else None,
                "grade": str(topic.grade_id) if topic.grade_id else None,
            }
            try:
                self.client.data_object.create(
                    class_name=self.weaviate_class_name,
                    uuid=topic.id,
                    data_object=data_object,
                )
                print(f"Assunto {topic.name} (cliente: {topic.client_id}) criado com sucesso")
            except ObjectAlreadyExistsException:
                self.client.data_object.update(
                    class_name=self.weaviate_class_name,
                    uuid=topic.id,
                    data_object=data_object,
                )
                print(f"Assunto {topic.name} (cliente: {topic.client_id}) atualizado com sucesso")
    
    def bulk_create_topics(self, topics):
        self.client.batch.configure(batch_size=100, num_workers=2)
        with self.client.batch as batch:
            for topic in topics:
                batch.add_data_object(
                    {
                        "name": topic.name,
                        "subject": str(topic.subject_id),
                        "client": str(topic.client_id) if topic.client_id else None,
                        "grade": str(topic.grade_id) if topic.grade_id else None,
                    },
                    self.weaviate_class_name,
                    uuid=topic.id,
                )
        
        print(f"Importação concluída! {topics.count()} assuntos importados.")

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
            topics = Topic.objects.all()
            self.bulk_create_topics(topics)
        else:
            topics = Topic.objects.filter(updated_at__date__gte=date)
            self.create_update_topics(topics)
