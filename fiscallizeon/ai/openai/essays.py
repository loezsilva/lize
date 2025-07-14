import base64
import json
from openai import OpenAI
from django.conf import settings
from fiscallizeon.ai.models import OpenAIQuery

gpt_model_image = 'gpt-4-vision-preview'
gpt_model_text = 'gpt-3.5-turbo-1106'
gpt_model_text_4 = 'gpt-4-turbo-preview'

def handle_essay(theme, content, essay_file):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # prompt para envio de imagem da redação
    transcription_prompt = "Você é um assistente para correção de redações criadas no modelo ENEM. Você receberá o texto escaneado e deve transcreve-lo para fazer sua avaliação. O texto é manuscrito e pode apresentar erros gramaticais ou caligrafia ruim, o que pode dificultar a leitura. Observe cada uma das linhas do texto, separadas visualmente por linhas finas horizontais. Atente-se à estrutura do texto, como parágrafos, quebras de linha ou palavras."

    #prompt para envio do texto transcrito
    pure_text_prompt = "Você é um assistente para correção de redações criadas no modelo ENEM. Você receberá o texto transcrito e deve avalia-lo."

    system_text = f"""
        {transcription_prompt if essay_file else pure_text_prompt}
        A redação possui como tema e texto base: "{theme}". Sua principal função é encontrar erros em pontos chave para correção de cada uma das competências no texto: 
        competência 1: erros de ortografia, acentuação ou pontuação.
        competência 2: trechos do texto que fujam do tema principal abordado.
        competência 3: falta de material que fortaleça os argumentos do autor, como dados estatíticos ou citações. Ao menos uma citação ou dado estatístico deve ser encontrado.
        competência 4: falta de elementos conectivos que conectem cada parágrafo do texto. É comum encontra-los no início dos parágrafos.
        competência 5: falta de um dos cinco elementos necessários na conclusão (ação, agente, modo/meio, efeito e detalhamento do efeito).
        Retorne true ou false para o encontro de erros e um detalhamento de quais erros foram encontrados para cada competência (Destaque no MÁXIMO 3 erros da competência 1).
        """

    post_prompt = """Retorne APENAS um JSON com a seguinte estrutura: {"competences": [{"competencia": <int>, "err": <bool>, "detail": ""}]}"""
        
    if essay_file:
        messages = [
                    {
                        "role": "system",
                        "content": system_text
                    },
                    {
                    "role": "user",
                    "content": [
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": essay_file,
                            "detail": "high"
                        }
                        }
                    ]
                    },
                    {
                    "role": "system",
                    "content": post_prompt
                    }
                ]

        # print("Gerando resposta...")
        gpt_response = client.chat.completions.create(
                model=gpt_model_image,
                messages=messages,
                temperature=0.2,
                max_tokens=4000,
            )
        
        response_json = gpt_response.choices[0].message.content.replace('json', '').replace('```', '')
        # print(response_json)
    
        return response_json

    else:
        messages = [
                {
                    "role": "system",
                    "content": system_text
                },
                {
                    "role": "user",
                    "content": content
                },
                {
                    "role": "system",
                    "content": post_prompt
                }
            ]
        
        # print("Gerando resposta...")
        gpt_response = client.chat.completions.create(
                model=gpt_model_text,
                messages=messages,
                temperature=0.2,
                max_tokens=4000,
            )
        
        response_json = gpt_response.choices[0].message.content.replace('json', '').replace('```', '')
        # print(response_json)

        return response_json
