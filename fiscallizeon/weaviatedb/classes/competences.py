competences_definition = {
    "class": "Competences",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
            "text2vec-openai": {},
            "generative-openai": {}
    },
    "invertedIndexConfig": {
        "indexNullState": True,
    },
    "properties": [
        {
            "name": "code",
            "dataType": ["text"]
        },
        {
            "name": "text",
            "dataType": ["text"]
        },
        {
            "name": "client",
            "dataType": ["uuid"]
        },
        {
            "name": "subject",
            "dataType": ["uuid"]
        },
        {
            "name": "knowledge_area",
            "dataType": ["uuid"]
        },
    ],
}