topics_definition = {
    "class": "Topics",
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
            "name": "name",
            "dataType": ["text"]
        },
        {
            "name": "subject",
            "dataType": ["uuid"]
        },
        {
            "name": "client",
            "dataType": ["uuid"]
        },
        {
            "name": "grade",
            "dataType": ["uuid"]
        },

    ],
}