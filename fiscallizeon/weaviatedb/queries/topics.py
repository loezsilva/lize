import weaviate

from django.conf import settings

from fiscallizeon.weaviatedb.classes.topics import topics_definition

class_name = topics_definition['class']

def search_topic(query, subject_ids, grade_id=None, client_id=None, limit=1):
    client_operand = {
        "path": ["client"],
        "operator": "IsNull",
        "valueBoolean": True,
    }

    if client_id:
        client_operand = {
            "path": ["client"],
            "operator": "Equal",
            "valueText": str(client_id),
        }

    where_filter = {
        "operator": "And",
        "operands": [
            client_operand,
            {
                "operator": "Or",
                "operands": [ 
                    {
                        "path": ["subject"],
                        "operator": "Equal",
                        "valueText": str(subject_id),
                    } for subject_id in subject_ids
                ]
            }
        ],
    }


    if grade_id:
        grade_operand = {
            "path": ["grade"],
            "operator": "Equal",
            "valueText": str(grade_id),
        }
        where_filter['operands'].append(grade_operand)


    try:
        client = weaviate.Client(
            url = settings.WEAVIATE_URL, 
            additional_headers = {
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )

        wv_response = (
            client.query
            .get(class_name, ["name", "client", "subject"])
            .with_near_text({
                "concepts": [query]
            })
            .with_where(where_filter)
            .with_limit(limit)
            .with_additional(['id', 'certainty'])
            .do()
        )

        topics = wv_response["data"]["Get"][class_name] or []
        response = []
        for topic in topics:
            response.append({
                "client": topic.get('client', None),
                "name": topic.get('name', None),
                **topic['_additional']
            })
        return response
    except KeyError as e:
        return {'error': wv_response.get('errors', e)}
    except Exception as e:
        return {'error': e}