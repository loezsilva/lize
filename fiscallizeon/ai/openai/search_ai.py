import base64
import json
from django.db.models import Q
from openai import OpenAI
from django.conf import settings
from fiscallizeon.subjects.models import Subject
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.exams.models import Exam
from django.urls import reverse
from fiscallizeon.ai.models import AIModel, OpenAIQuery

gpt_model = 'gpt-4-1106-preview'
gpt_model_image = 'gpt-4-vision-preview'

def mount_query_operation(user, who, who_name, operation, period=None, what=None, what_names=None):
    
    print(who, who_name, operation, period, what, what_names)

    objects = None

    if who == 'student':
        objects = Student.objects.filter(name__unaccent__icontains=who_name).distinct()[:3]
    elif who == 'classe':
        objects = SchoolClass.objects.filter(
            Q(name__unaccent__icontains=who_name) |
            Q(coordination__unity__name__unaccent__icontains=who_name)
        ).distinct()[:3]
    
    if what:

        if what == 'exams':
            
            try:
                if type(what_names) == str:
                    whats = Exam.objects.filter(name__unaccent__icontains=what_names).distinct()
                else:
                    whats = Exam.objects.filter(name__unaccent__in=what_names).distinct()
            except Exception as e:
                print(e)
            
        if what == 'subjects':
            
            try:
                if type(what_names) == str:
                    whats = user.get_availables_subjects().filter(name__unaccent__icontains=what_names).distinct()
                else:
                    whats = user.get_availables_subjects().filter(name__unaccent__in=what_names).distinct()
            except Exception as e:
                print(e)

    mounted_urls = []

    for object in objects:
        i = {}
        
        i['who'] = who
        i['name'] = object.__str__()
        i['url'] = f'{reverse("dashboards:dashboards")}?who={who}&who_id={object.id}'

        if period:
            i['url'] += f'&period={period}'

        if what:
            i['url'] += f'&what={what}&what_ids='
            for what in whats:
                i['url'] += f'{str(what.id)},'
            
            i['url'].replace(',', '')

        mounted_urls.append(i)

    return mounted_urls


"""
    TODO: super search
"""
def search(user, user_prompt):
    system_prompt = f"""
        Generate a Django function to fetch data based on the following query: {user_prompt}
    """

    post_prompt = ("""
        
    """)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    gpt_response = client.chat.completions.create(
        model='gpt-4o',
        messages=messages,
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "mount_query_operation",
                    "description": "Gera a query para um operação no banco de dados",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "who": {
                                "type": "string", 
                                "enum": [
                                    "student", 
                                    "classe", 
                                    "exam",
                                ],
                                "description": "O quem pode ser aluno, turma ou caderno de prova",
                            },
                            "who_name": {
                                "type": "string", 
                                "description": "O nome do termo procurado",
                            },
                            "operation": {
                                "type": "string", 
                                "enum": [
                                    "get_avg", 
                                    "get_histogram", 
                                    "get_subjects_avg",
                                ],
                                "description": "A operação retorna os dados que o usuário está buscando, exemplo: get_avg retorna uma média",
                            },
                            "period": {
                                "type": "string", 
                                "enum": [
                                    "period", 
                                    "semenstral", 
                                    "last_year",
                                    "last_month",
                                    "last_7_days",
                                    "all"
                                ],
                                "description": "Período da busca se houver",
                            },
                            "what": {
                                "type": "string", 
                                "enum": [
                                    "subjects", 
                                    "classes", 
                                    "exams",
                                ],
                                "description": "O nome do termo procurado",
                            },
                            "what_names": {
                                "type": "string", 
                                "description": "Retorne um array, esse parametro é opcional e pode ser utilizado junto com o who, exemplo: na operation: get_avg eu poderia juntar com o what como pesquisar a média de um student nas subjects what_names: ['matematica', 'ciencias']",
                            },
                        },
                        "required": [
                            "who", 
                            "who_name", 
                            "operation",
                            "period"
                        ],
                    },
                },
            }
        ],
        tool_choice="auto",
        max_tokens=2048,
    )

    openai_query = OpenAIQuery.objects.create(
        user_prompt=user_prompt,
        gpt_model='gpt-4o',
        prompt_category=OpenAIQuery.QUESTION_GENERATION,
        user=user,
        ai_model=AIModel.objects.get(identifier='gpt-4o'),
    )

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    try:

        response_message = gpt_response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:

            available_functions = {
                "mount_query_operation": mount_query_operation,
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                
                function_response = function_to_call(
                    user=user,
                    who=function_args.get("who"),
                    who_name=function_args.get("who_name"),
                    operation=function_args.get("operation"),
                    period=function_args.get("period"),
                    what=function_args.get("what"),
                    what_names=function_args.get("what_names"),
                )

                return function_response
        
    except Exception as e:
        print(e)
