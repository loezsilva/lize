import weaviate

from django.conf import settings

from fiscallizeon.weaviatedb.classes.abilities import abilities_definition

class_name = abilities_definition['class']

def search_ability(query, grade_id, client_id=None, subject_ids=[], knowledge_area_id=None, limit=1):
    where_filter = {
        "operator": "And",
        "operands": [ 
            {
                "path": ["grades"],
                "operator": "ContainsAny",
                "valueText": [str(grade_id)],
            },
        ]
    }

    client_conditions = {
        "operator": "Or",
        "operands": [
            {
                "path": ["client"],
                "operator": "IsNull",
                "valueBoolean": True,
            }
        ]
    }

    if client_id:
        client_conditions['operands'].append({
            "path": ["client"],
            "operator": "Equal",
            "valueText": str(client_id),
        })

    where_filter['operands'].append(client_conditions)

    if subject_ids:
        subject_conditions = {
            "operator": "Or",
            "operands": [
                {
                    "path": ["subject"],
                    "operator": "IsNull",
                    "valueBoolean": True,
                }
            ]
        }
        for subject_id in subject_ids:
            subject_conditions['operands'].append({
                "path": ["subject"],
                "operator": "Equal",
                "valueText": str(subject_id),
            })

        where_filter['operands'].append(subject_conditions)

    if knowledge_area_id:
        knowledge_area_conditions = {
            "operator": "Or",
            "operands": [
                {
                    "path": ["subject"],
                    "operator": "IsNull",
                    "valueBoolean": True,
                },
                {
                    "path": ["subject"],
                    "operator": "Equal",
                    "valueText": str(knowledge_area_id),
                }
            ]
        }
        where_filter['operands'].append(knowledge_area_conditions)

    try:
        client = weaviate.Client(
            url = settings.WEAVIATE_URL, 
            additional_headers = {
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )
        
        wv_response = (
            client.query
            .get(class_name, ["code", "text", "client"])
            .with_near_text({
                "concepts": [query]
            })
            .with_where(where_filter)
            .with_limit(limit)
            .with_additional(['id', 'certainty'])
            .do()
        )
        
        abilities = wv_response["data"]["Get"][class_name]

        response = []
        for ability in abilities:
            response.append({
                "client": ability.get('client', None),
                "code": ability.get('code', None),
                "text": ability.get('text', None),
                **ability['_additional']
            })
        return response
    except KeyError as e:
        print(e)
        return {'error': wv_response.get('errors', e)}
    except Exception as e:
        return {'error': e}