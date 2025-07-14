import weaviate
from weaviate.exceptions import UnexpectedStatusCodeException

from django.conf import settings

client = weaviate.Client(
    url = settings.WEAVIATE_URL, 
    additional_headers = {
        "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
    }
)

public_questions_definition = {
    "class": "PublicQuestions",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
            "text2vec-openai": {},
            "generative-openai": {}
    },
    "properties": [
        {
            "name": "enunciation",
            "dataType": ["text"]
        },
        {
            "name": "commented_awnser",
            "dataType": ["text"]
        },
        {
            "name": "alternatives",
            "dataType": ["text[]"]
        },
    ],
}

try:
    client.schema.delete_class(public_questions_definition['class'])
    client.schema.create_class(public_questions_definition)
    print("Schema created")
except UnexpectedStatusCodeException:
    client.schema.update_config(public_questions_definition['class'], public_questions_definition)
    print("Schema updated")