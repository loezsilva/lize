import os
import json
import tempfile
import requests

from google.cloud import language_v1

from fiscallizeon.core.gcp.utils import _get_service_account_json


def get_text_entities(text_content):
    account_info = _get_service_account_json()

    tf = tempfile.NamedTemporaryFile()
    tf.write(json.dumps(account_info).encode('utf-8'))
    tf.seek(0)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tf.name

    client = language_v1.LanguageServiceClient()

    # Available types: PLAIN_TEXT, HTML
    type_ = language_v1.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    language = "pt-br"
    document = {"content": text_content, "type_": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = language_v1.EncodingType.UTF8

    response = client.analyze_entities(request = {'document': document, 'encoding_type': encoding_type})

    entities = []
    for entity in response.entities:
        
        if not entity.name:
            print("$$$")
            continue

        entity_dict = {
            'value': entity.name,
            'salience': entity.salience or 0,
            'type': entity.type,
        }
        entities.append(entity_dict)

    return entities
