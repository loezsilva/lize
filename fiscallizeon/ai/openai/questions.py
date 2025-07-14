import base64
import json
from openai import OpenAI
from django.conf import settings
from fiscallizeon.ai.models import AIModel, OpenAIQuery
import json_repair
from .utils import remove_nested_math_tags, replace_latex_with_mathml

gpt_model = 'gpt-4-1106-preview'
gpt_model_image = 'gpt-4-vision-preview'
gpt_model_4o = 'gpt-4o'
gpt_model_4o_mini = 'gpt-4o-mini'
gpt_3 = 'gpt-3.5-turbo-1106'

def create_new_question(user, user_prompt, items=[], alternatives_quantity=5):
    competences_and_abilities = [item['text'] for item in items]

    system_prompt = f"""
    A questão deve conter um texto base de contextualização e um enunciado com a pergunta.
    Case a questão que o usuário pediu seja uma questão objetiva crie exatamente {alternatives_quantity} alternativas com apenas uma delas sendo correta. 
    Não utilize quaisquer referências a imagens. 
    Siga as seguintes competências e habilidades (caso existam) e as informações do usuário como prioridade para a criação da questão:
    {competences_and_abilities}
    """

    post_prompt = 'Formate fórmulas e equações utilizando o formato MathML. Retorne APENAS um JSON com o seguinte formato \
    {"base_text": "", "enunciation": "", "commented_answer": ""}\
    o campo enunciation deve possuir formatação HTML\
    caso a questão seja objetiva adicione "alternatives":[{"text":"", "is_correct": <bool>}] ao JSON'
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ai_model = AIModel.objects.get(identifier=gpt_3)
    ai_model = AIModel.objects.get(identifier=gpt_model_4o)

    openai_query = OpenAIQuery.objects.create(
        user_prompt=user_prompt,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_GENERATION,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.8,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    content = (
        gpt_response.choices[0].message.content
    )

    # Tenta converter ou reparar o JSON
    try:
        response_json = json.loads(content)
    except Exception:
        response_json = json_repair.loads(content)

    try: # Tenta aplicar os replaces
        enunciation = response_json.get('enunciation')
        base_text = response_json.get('base_text')
        response_json['enunciation'] = enunciation.replace("\n", "<br>")
        response_json['base_text'] = base_text.replace("\n", "<br>")
    except Exception:
        pass

    return response_json


def create_new_question_efaf(user, user_prompt):
    system_prompt = """
    Elabore uma questão de dificuldade alta para alunos do ensino fundamental de 5º a 9º ano.
    A questão deve conter um texto base de contextualização e um enunciado com a pergunta.
    Seja sucinto na elaboração do texto base.
    Crie exatamente cinco alternativas com apenas uma delas sendo correta. 
    Não utilize quaisquer referências a imagens.
    Evite utilizar ou redigir texto-base, enunciado e alternativas que possam induzir o aluno do teste ao erro.
    Evite abordagens de temas que suscitem polêmicas.
    Elabore o enunciado seguindo as regras abaixo:
    - Utilize termos impessoais como: “considere-se”, “calcula-se”, “argumenta-se”;
    - Não utilize termos como: “falso”, “exceto”, “incorreto”, “não”, “errado”;
    - Não utilize termos absolutos como: “sempre”, “nunca”, “todo”, “totalmente”;
    - Não utilize sentenças como: “Pode-se afirmar que”, “É correto afirmar que”;
    Construa as alternativas seguinto as regras abaixo:
    - Com paralelismo sintático e semântico, extensão equivalente e coerência com o enunciado;
    - Independentes umas das outras, de maneira que não sejam excludentes, negando informações do texto, nem semanticamente muito próximas;
    - Dispostas de maneira lógica (sequência narrativa, alfabética, crescente/decrescente • etc.);
    - Evite repetição de palavras que aparecem no enunciado;
    - Evite alternativas demasiadamente longas;
    - Não use: “todas as anteriores”, “nenhuma das anteriores”;
    - O gabarito deve estar exposto de forma clara, ser a única alternativa correta e não deve ser mais atrativo que os distratores;
    - Os distratores não devem ser absurdos em relação à situação-problema apresentada
    Utilize as informações do usuário como prioridade para geração da nova questão caso haja divergência com as informações acima
    """

    post_prompt = 'Formate fórmulas e equações utilizando o formato MathML. Retorne APENAS um JSON com o seguinte formato \
      {"base_text": "", "enunciation": "", "alternatives":[{"text":"", "is_correct": <bool>}], "commented_answer": ""}\
      o campo enunciation deve possuir formatação HTML'
      

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    gpt_model = 'gpt-4-1106-preview'

    ai_model = AIModel.objects.get(identifier=gpt_model_4o)

    openai_query = OpenAIQuery.objects.create(
        user_prompt=user_prompt,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_GENERATION,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    content = gpt_response.choices[0].message.content
    response_json = json.loads(content)
    return response_json


def create_new_image_question(user, user_prompt, base_image, alternatives_quantity=5):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = f"""
    Utilizando a imagem como base elabore uma questão. 
    A questão deve conter um texto base de contextualização relacionado à imagem e um enunciado com a pergunta.
    Caso necessário omita o texto base, Caso utilize-o, não exceda 20 palavras.
    Case a questão que o usuário pediu seja uma questão objetiva crie exatamente {alternatives_quantity} alternativas com apenas uma delas sendo correta. 
    Considere que a imagem ficará situada sempre acima do texto base. 
    Evite utilizar ou redigir texto-base, enunciado e alternativas que possam induzir o aluno do teste ao erro.
    Evite abordagens de temas que suscitem polêmicas.
    Elabore o enunciado seguindo as regras abaixo:
    - Utilize termos impessoais como: “considere-se”, “calcula-se”, “argumenta-se”;
    - Não utilize termos como: “falso”, “exceto”, “incorreto”, “não”, “errado”;
    - Não utilize termos absolutos como: “sempre”, “nunca”, “todo”, “totalmente”;
    - Não utilize sentenças como: “Pode-se afirmar que”, “É correto afirmar que”;
    Construa as alternativas seguinto as regras abaixo:
    - Com paralelismo sintático e semântico, extensão equivalente e coerência com o enunciado;
    - Independentes umas das outras, de maneira que não sejam excludentes, negando informações do texto, nem semanticamente muito próximas;
    - Dispostas de maneira lógica (sequência narrativa, alfabética, crescente/decrescente • etc.);
    - Evite repetição de palavras que aparecem no enunciado;
    - Evite alternativas demasiadamente longas;
    - Evite alternativas muito óbvias;
    - Não use: “todas as anteriores”, “nenhuma das anteriores”;
    - O gabarito deve estar exposto de forma clara, ser a única alternativa correta e não deve ser mais atrativo que os distratores;
    - Os distratores não devem ser absurdos em relação à situação-problema apresentada
    Utilize as informações do usuário como prioridade para geração da nova questão caso haja divergência com as informações acima
    """

    user_prompt_dict = [
        {
            "type": "image_url",
            "image_url": {
                "url": base_image,
                "detail": "high"
            },
        },
        {
            "type": "text",
            "text": user_prompt,
        },
    ]

    post_prompt = 'Os textos devem estar formatados em HTML. \
    Formate todas as fórmulas matemáticas e equações utilizando o formato MathML. Retorne APENAS um JSON com o seguinte formato \
    {"base_text": "", "enunciation": "", "commented_answer": ""} \
    caso a questão seja objetiva adicione "alternatives":[{"text":"", "is_correct": <bool>}] ao JSON'

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_dict},
        {"role": "system", "content": post_prompt},
    ]
    try:

        gpt_response = client.chat.completions.create(
            model=gpt_model_4o,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        ai_model = AIModel.objects.get(identifier=gpt_model_4o)

        openai_query = OpenAIQuery.objects.create(
            user_prompt=user_prompt,
            gpt_model=gpt_model_4o,
            prompt_category=OpenAIQuery.QUESTION_GENERATION,
            user=user,
            ai_model=ai_model,
        )

        openai_query.input_tokens = gpt_response.usage.prompt_tokens
        openai_query.output_tokens = gpt_response.usage.completion_tokens
        openai_query.cost = openai_query.get_calculated_cost()
        openai_query.finish_reason = gpt_response.choices[0].finish_reason
        openai_query.save()

        content = (
            gpt_response.choices[0].message.content
        )

        # Tenta converter ou reparar o JSON
        try:
            response_json = json.loads(content)
        except Exception:
            response_json = json_repair.loads(content)

        try: # Tenta aplicar os replaces
            enunciation = response_json.get('enunciation')
            base_text = response_json.get('base_text')
            response_json['enunciation'] = enunciation.replace("\n", "<br>")
            response_json['base_text'] = base_text.replace("\n", "<br>")
        except Exception:
            pass
        
        response_json['base_image'] = base_image
        
        return response_json
    
    except Exception as e:
        print(e)
        
    return None


def improve_question(user, question):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = """
    você é um revisor ortogáfico super crítico de uma escola

    - Você receberá um JSON de uma questão formatada em HTML. A questão poderá ser discursiva ou objetiva. 
    - Analise o texto do enunciado e alternativas e proponha melhorias de concordância, pontuação,
    - ortografia e coesão, evitando a repetição de palavras, trocando-as por sinônimos quando necessário. 
    - Use o campo enunciation para trazer a correção do enunciado, e alternatives para trazer a correção das alternativas se houver
    - Elabore também um pequeno texto impessoal e na voz passiva explicando as alterações realizadas na questão original, no campo correction_detail.
    - Verifique se há alternativas duplicadas e sugira novas alternativas se ncessário.
    """

    
    post_prompt = 'Mantenha a formatação HTML da questão original. Escape aspas duplas da questão original. \
        Não modifique os nomes dos campos no JSON original. Retorne apenas um JSON na seguinte formatação \
      {"enunciation": "", "alternatives":[{"text":"", "is_correct": <bool>}], "correction_detail": ""}'

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    ai_model = AIModel.objects.get(identifier=gpt_model_4o)

    openai_query = OpenAIQuery.objects.create(
        user_prompt=question,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_IMPROVEMENT,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.2,
        response_format={ "type": "json_object"}
    )

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    content = gpt_response.choices[0].message.content
    
    try:
        
        response_json = json.loads(content)
        
        return response_json, 200

    except Exception as e:
        print(e)
        return { 'errors': 'GPT error' }, 400


def solve_question(user, question):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = """
    Você receberá uma questão objetiva ou discursiva. Elabore uma resolução para essa questão.
    Para facilitar a compreensão você pode optar em separar a resposta em parágrafos.
    Retorne o texto formatado em um HTML simples, sem títulos ou subtítulos para os parágrafos.
    Não é necessário introduzir a questão em sua resposta, forneça apenas a resolução.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    ai_model = AIModel.objects.get(identifier=gpt_model_4o)

    openai_query = OpenAIQuery.objects.create(
        user_prompt=question,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_SOLVING,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.2,
    )

    if not gpt_response.choices:
        print(gpt_response)
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    try:
        content = gpt_response.choices[0].message.content
        return {'resolution': content}
    except:
        return {'error': 'GPT error'}


def handle_textual_answer(enunciation, commented_answer, student_answer, question_file, user=None):

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    system_prompt = f"""
    Aja como um corretor de questões discursivas.
    Você receberá uma resposta de um aluno, e deverá corrigi-la com base no exemplo de resposta correta. Não são esperadas informações além do que a questão solicita, caso o aluno forneça todos os tópicos esperados pelo exemplo, atribua nota máxima.
    O enunciado da questão é: {enunciation}.
    O exemplo de resposta correta é: {commented_answer}.
    Retorne uma porcentagem (em valores entre 0 e 1, em incrementos de 0.25) de acerto do aluno. Use o exemplo como referência para a correção. Faça um breve comentário em terceira pessoa sobre a razão da sua avaliação. Também elabore um feedback que será lido pelo aluno, tal qual um professor faria, em tom incentivativo e sugerindo ações caso necessário.
    """
    post_prompt = """Retorne APENAS um JSON com o seguinte formato {"percentage": <float>, "comment": "", "feedback": ""}"""

    if question_file:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {
                    "type": "image_url",
                    "image_url": {
                            "url": question_file,
                            "detail": "high"
                        }
                }
            ]},
            {"role": "system", "content": post_prompt},
        ]

        ai_model = AIModel.objects.get(identifier=gpt_model_4o)
        openai_query = OpenAIQuery.objects.create(
            user_prompt="Gerado pela lize.",
            user=user,
            gpt_model=gpt_model_4o,
            prompt_category=OpenAIQuery.ANSWER_CORRECTION,
            ai_model=ai_model,
        )

        # print("Gerando resposta...")
        gpt_response = client.chat.completions.create(
            model=gpt_model_4o,
            messages=messages,
            temperature=0.2,
            max_tokens=4000,
        )

        openai_query.input_tokens = gpt_response.usage.prompt_tokens
        openai_query.output_tokens = gpt_response.usage.completion_tokens
        openai_query.cost = openai_query.get_calculated_cost()
        openai_query.save()

        response_json = gpt_response.choices[0].message.content.replace('json', '').replace('```', '')
        return response_json

    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": student_answer},
            {"role": "system", "content": post_prompt},
        ]

        # print("Gerando resposta...")
        gpt_response = client.chat.completions.create(
            model=gpt_model_4o,
            messages=messages,
            temperature=0.2,
            max_tokens=4000,
        )

        response_json = gpt_response.choices[0].message.content.replace('json', '').replace('```', '')
        return response_json


def create_new_questions_for_item_request(user, user_prompt, support_image=None):

    system_prompt = f"""
    A questão deve conter um texto base de contextualização e um enunciado com a pergunta.
    Crie exatamente CINCO alternativas com apenas uma delas sendo correta. 
    As alternativas devem ser diversas, coerentes com o enunciado, e cada uma deve explorar um conceito diferente relacionado ao tema da pergunta.
    Evite qualquer repetição de conteúdo entre as alternativas. 
    Evite utilizar ou redigir texto-base, enunciado e alternativas que possam induzir o aluno do teste ao erro.
    Evite abordagens de temas que suscitem polêmicas.
    Elabore o enunciado seguindo as regras abaixo:
    - Utilize termos impessoais como: “considere-se”, “calcula-se”, “argumenta-se”;
    - Não utilize termos como: “falso”, “exceto”, “incorreto”, “não”, “errado”;
    - Não utilize termos absolutos como: “sempre”, “nunca”, “todo”, “totalmente”;
    - Não utilize sentenças como: “Pode-se afirmar que”, “É correto afirmar que”;

    Construa as alternativas seguindo as regras abaixo:
    - Assegure que cada alternativa seja única e explore aspectos diferentes do conteúdo abordado no enunciado;
    - Use paralelismo sintático e semântico, extensão equivalente e coerência com o enunciado;
    - As alternativas devem ser independentes umas das outras, sem se contradizer ou serem muito semelhantes entre si;
    - Dispostas de maneira lógica (sequência narrativa, alfabética, crescente/decrescente, etc.);
    - Evite repetição de palavras que aparecem no enunciado;
    - Evite alternativas demasiadamente longas;
    - Evite alternativas muito óbvias;
    - Não use: “todas as anteriores”, “nenhuma das anteriores”;
    - O gabarito deve estar exposto de forma clara, ser a única alternativa correta e não deve ser mais atrativo que os distratores;
    - Os distratores não devem ser absurdos em relação à situação-problema apresentada.

    Utilize as informações do usuário como prioridade para a geração da nova questão, caso haja divergência com as informações acima.

    Se a questão tiver formulas matemáticas, gere apenas MathML com a tag <math>, nunca gere formulas com KaTeX 
    NUNCA GERE FORMULAS COMO ESSE EXEMPLO: \\( x = 2 \\) e \\( x = 3 \\) AO INVÉS DISSO, GERE FORMULAS COM A TAG: <math>
    """

    if support_image:
        user_prompt = [
            {
                "type": "image_url",
                "image_url": {
                    "url": support_image,
                    "detail": "high"
                },
            },
            {
                "type": "text",
                "text": user_prompt,
            },
        ]
        system_prompt += "Elabore a questão levando em consideração a imagem e o que foi solicitado como base, use-a como contextualização para gerar o enunciado."

    post_prompt = 'Formate fórmulas e equações utilizando o formato MathML, nunca KaTeX. Retorne APENAS um JSON com o seguinte formato \
    {"base_text": "", "enunciation": "", "commented_answer": ""}\
    o campo enunciation deve possuir formatação HTML\
    caso a questão seja objetiva adicione "alternatives":[{"text":"", "is_correct": <bool>}] ao JSON'
    

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    ai_model = AIModel.objects.get(identifier='gpt-4o')

    openai_query = OpenAIQuery.objects.create(
        user_prompt=user_prompt,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_GENERATION,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.8,
        max_tokens=2048
    )

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()
    content = gpt_response.choices[0].message.content.replace('json', '').replace('```', '').replace( "\\",  "\\\\").replace( '\\"',  '"')

    # Faz a substituição de Katex para Mathml utilizando lib latex2mathml
    content = replace_latex_with_mathml(content)

    # Remove tags Math dentro de outra tag Math para resolver
    # problema de formulas geradas com Mathtype error
    # task: https://app.clickup.com/t/86a7r1dyv
    content = remove_nested_math_tags(content)

    # Tenta converter ou reparar o JSON
    try:
        response_json = json.loads(content)
    except:
        response_json = json_repair.loads(content)

    return response_json

def create_new_version_question_ia(user, user_prompt):
    import re
    system_prompt = """
        Você é um professor especializada em gerar novas versões de questões, tanto de múltipla escolha quanto discursivas. Sua tarefa é reescrever a questão com base nas instruções específicas fornecidas, que podem variar de acordo com o tipo da questão. 
        Voce irá receber uma questão em Html e deverá seguir todas as instruções que virá junto a questão.
        Se múltiplas instruções forem fornecidas, atenda a todas as instruções indicadas.
        """


    post_prompt = '''
    Formate fórmulas e equações utilizando o formato MathML. Retorne APENAS um JSON com o seguinte formato \
    {"enunciation": "", "commented_answer": ""}\
    o campo enunciation deve possuir formatação HTML.\
    Caso a questão seja objetiva, adicione "alternatives":[{"text":"", "is_correct": <bool>}] ao JSON
    '''
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": post_prompt},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    ai_model = AIModel.objects.get(identifier='gpt-4o')

    openai_query = OpenAIQuery.objects.create(
        user_prompt=user_prompt,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_GENERATION,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.8,
        max_tokens=2048
    )
    

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    fixed_content = gpt_response.choices[0].message.content.replace('json', '').replace('```', '').replace( "\\",  "\\\\").replace('\\"', '"')

    response_json = json.loads(fixed_content)
    return response_json

def create_adapted_question(user, prompt):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = """
        Você é um especialista em revisão ortográfica, gramatical e em criação de questões adaptadas para uma escola.

        - Você receberá um JSON contendo uma questão formatada em HTML, que pode ser discursiva ou objetiva.
        - Suas tarefas devem ser realizadas apenas se forem explicitamente solicitadas no prompt do usuário. As possíveis tarefas incluem:
        1. **Melhorar o enunciado e as alternativas**: Ajuste a concordância verbal e nominal, pontuação, ortografia e coesão, evitando a repetição de palavras e sugerindo sinônimos quando apropriado. 
        Respeite a indicação da alternativa correta, caso a mesma venha indicada.
        2. **Adaptar e simplificar**: Se solicitado, adapte o nível da questão para torná-la mais acessível, simplificando a linguagem ou o conteúdo, sem modificar o significado ou os objetivos pedagógicos.
        3. **Respeitar a extensão**: Não reduza o enunciado ou as alternativas, a menos que explicitamente solicitado.
        - O campo 'enunciation' deve conter a versão corrigida do enunciado apenas se isso for solicitado.
        - O campo 'alternatives' deve conter as alternativas corrigidas e adaptadas, apenas se solicitado.
        4. **Não modifique o Html, a não ser que isso seja explicitamente solicitado.

    """

   
    post_prompt = 'Formate fórmulas e equações utilizando o formato MathML. Retorne APENAS um JSON com o seguinte formato \
      {"enunciation": ""}\
      o campo enunciation deve possuir formatação HTML\
      caso a questão seja objetiva adicione "alternatives":[{"text":"", "is_correct": <bool>}] ao JSON'


    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},  
        {"role": "system", "content": post_prompt},
    ]

    ai_model = AIModel.objects.get(identifier='gpt-4o')

    openai_query = OpenAIQuery.objects.create(
        user_prompt=prompt,
        gpt_model=gpt_model_4o,
        prompt_category=OpenAIQuery.QUESTION_IMPROVEMENT,
        user=user,
        ai_model=ai_model,
    )

    gpt_response = client.chat.completions.create(
        model=gpt_model_4o,
        messages=messages,
        temperature=0.8,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )
    

    if not gpt_response.choices:
        return {'error': 'GPT error'}

    openai_query.input_tokens = gpt_response.usage.prompt_tokens
    openai_query.output_tokens = gpt_response.usage.completion_tokens
    openai_query.cost = openai_query.get_calculated_cost()
    openai_query.finish_reason = gpt_response.choices[0].finish_reason
    openai_query.save()

    content = gpt_response.choices[0].message.content

    # Tenta converter ou reparar o JSON
    try:
        response_json = json.loads(content)
    except Exception:
        response_json = json_repair.loads(content)

    try: # Tenta aplicar os replaces
        enunciation = response_json.get('enunciation')
        response_json['enunciation'] = enunciation.replace("\n", "<br>")
    except Exception:
        pass

    response_json = json.loads(content)
    return response_json