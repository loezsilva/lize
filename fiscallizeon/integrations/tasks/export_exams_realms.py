import re
import requests
from bs4 import BeautifulSoup, NavigableString

from celery import states
from decouple import config
from sentry_sdk import capture_message

from django.utils import timezone
from django.db.models import Q, F, Count, Window
from django.db.models.functions import Rank
from django.template.defaultfilters import slugify


from fiscallizeon.celery import app
from fiscallizeon.clients.models import Client
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.integrations import realms
from fiscallizeon.integrations.models import Integration, AbilityCode, CompetenceCode, TopicCode, SubjectCode
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

def _convert_html_to_katex(html):
    katex_service_url = config('KATEX_SERVICE_ADRRESS', default='')

    if not katex_service_url:
        return html
    
    try:
        response = requests.post(
            katex_service_url + '/convert_mml_latex',
            json={'text': html}
        )
        
        if response.status_code == 200:
            return response.json().get('converted_text', html)

    except Exception as e:
        print(e)
        capture_message("Erro na conversão do HTML para katex:", str(e))
    
    return html

def _replace_img_srcs(client, html):
    pattern = r'(<img[^>]*\s+src\s*=\s*)(["\']?)([^"\'>\s]+)(\2)'

    def _replace_re(match):
        prefix = match.group(1)
        quotes = match.group(2)
        old_src = match.group(3)
        try:
            new_src = realms.upload_image(client, old_src).get('url', old_src)
        except:
            return old_src
        return f'{prefix}{quotes}{new_src}{quotes}'

    return re.sub(pattern, _replace_re, html, flags=re.IGNORECASE)

def _clear_html(html):
    def _translate_elements(elements):
        html_elements = str(elements)

        try:
            response = requests.post('http://172.17.0.1:5000/convert_html_quill', json={"text": html_elements})
            response.raise_for_status()
            
            new_html = response.json().get("converted_text")

            if not new_html:
                raise ValueError("Resposta da API não contém 'html'.")

            new_elements = BeautifulSoup(new_html, 'html.parser')
            return new_elements.contents[0]

        except Exception as e:
            print(f"[Erro] Falha ao processar lista via API: {e}")
            return elements 

    soup = BeautifulSoup(html, 'html.parser')

    #Removendo espaços em branco entre as tags
    for element in soup.find_all(text=True):
        if isinstance(element, NavigableString) and element.strip() == "":
            element.extract()

    #Transormando listas e listas ordenadas em quill
    for elements in soup.find_all(['ul', 'ol']):
        new_elements = _translate_elements(elements)
        elements.replace_with(new_elements)

    #Removendo spans vazios
    for span in soup.find_all('span'):
        #Ignorando os spans de bullet lists do Quill
        if 'ql-ui' in span.get("class", []):
            continue

        has_text = span.get_text(strip=True) != ""
        has_tags = any(child.name for child in span.children)
        if not has_text and not has_tags:
            span.decompose()

    #Removendo parágrafos vazios
    for p in soup.find_all('p'):
        has_text = p.get_text(strip=True) != ""
        has_tags = any(child.name for child in p.children)
        if not has_text and not has_tags:
            p.decompose()

    #Adicionando margem nas imagens e divs
    for img in soup.find_all('img'):
        current_style = img.get('style', '')
        if current_style and not current_style.strip().endswith(';'):
            current_style += ';'

        new_style = current_style + 'margin-top: 25px;'
        img['style'] = new_style

    #Adicionando margens às divs de nível zero para manter consistência
    divs = soup.find_all(['div', 'p'], recursive=False)
    total_divs = len(divs)
    for index, div in enumerate(divs):
        current_style = div.get('style', '')
        if current_style and not current_style.strip().endswith(';'):
            current_style += ';'

        if index == 0:
            div['style'] = current_style + 'margin-bottom: 15px;'
        elif index == total_divs - 1:
            div['style'] = current_style + 'margin-top: 15px;'
        else:
            div['style'] = current_style + 'margin-top: 15px; margin-bottom: 15px;'


    return str(soup)

def _format_cloze_question(text):
    pattern = re.compile(r'\[\[(.*?)\]\]')
    result = []
    last_end = 0

    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            before = text[last_end:start]
            result.append({
                "type": "text",
                "value": before
            })

        result.append({
            "type": "select",
            "value": match.group(1)
        })
        last_end = end

    if last_end < len(text):
        result.append({
            "type": "text",
            "value": text[last_end:]
        })

    return result

def _mount_question_json(exam_question, client, section_order, ets_index):
    question = {
        'key': f'{exam_question.short_code}-{str(exam_question.id)[:8]}',
        'required': True,
        'order': exam_question.rank + section_order,
        'section': ets_index,
        'shuffle': True,
        'categories': [],
        'score': f'{float(exam_question.weight)}',
        'comment': '',
    }

    if exam_question.question.category == Question.CLOZE:
        question['type'] = 'fill-words'
    elif exam_question.question.category == Question.CHOICE:
        is_multiple_choice = len(exam_question.question.correct_alternatives) > 1 
        question['type'] = 'multi' if is_multiple_choice else 'single'

    question['statement'] = exam_question.question.enunciation

    #Substituindo as imagens
    if 'fiscallizeremote.nyc3' in exam_question.question.enunciation:
        question['statement'] = _replace_img_srcs(client, question['statement'])

    if '</math>' in exam_question.question.enunciation:
        question['statement'] = _convert_html_to_katex(question['statement'])

    # Ajustando casos com listagens
    question['statement'] = _clear_html(question['statement'])

    if id_erp := exam_question.id_erp:
        question['id'] = id_erp

    # if exam_question.question.commented_awnser:
    #     question[''] = exam_question.question.get_commented_awnser_str()

    subject = exam_question.exam_teacher_subject.teacher_subject.subject

    subject_code = SubjectCode.objects.filter(
        client=client,
        subject=subject,
    ).last()

    if not subject_code:
        message = f'Não foi possível encontrar o código do assunto {subject.name} para o cliente {client.name}'
        capture_message('Erro de integração com realms: ', message)
        print(message)
        raise Exception(message)

    question['categories'].append({'id': int(subject_code.code)})

    #Sincroniza tópicos, habilidades e competências no realms caso não tenham sincronizado antes
    not_sync_topics = exam_question.question.topics.filter(codes__isnull=True)
    for _topic in not_sync_topics:
        _topic.update_erp(subject)

    not_sync_abilities = exam_question.question.abilities.filter(codes__isnull=True)
    for _abi in not_sync_abilities:
        _abi.client = client
        _abi.update_erp(subject)

    not_sync_competences = exam_question.question.competences.filter(codes__isnull=True)
    for _comp in not_sync_competences:
        _comp.client = client
        _comp.update_erp(subject)

    if topics := exam_question.question.topics.all():
        codes = TopicCode.objects.filter(
            client=client,
            topic__in=topics
        ).values_list('code', flat=True)

        codes_int = [{'id': int(c)} for c in codes]
        question['categories'].extend(codes_int)

    if abilities := exam_question.question.abilities.all():
        codes = AbilityCode.objects.filter(
            client=client,
            ability__in=abilities,
        ).values_list('code', flat=True)

        codes_int = [{'id': int(c)} for c in codes]
        question['categories'].extend(codes_int)

    if competences := exam_question.question.competences.all():
        codes = CompetenceCode.objects.filter(
            client=client,
            competence__in=competences,
        ).values_list('code', flat=True)
        
        codes_int = [{'id': int(c)} for c in codes]
        question['categories'].extend(codes_int)

    if exam_question.question.category == Question.CHOICE:
        question['options'] = {}
        for index, alternative in enumerate(exam_question.question.alternatives.all().order_by('index')):
            option_text = alternative.text

            if 'fiscallizeremote.nyc3' in alternative.text:
                option_text = _replace_img_srcs(client, alternative.text)

            if '</math>' in alternative.text:
                option_text = _convert_html_to_katex(alternative.text)

            question['options'][index] = {
                'id': str(exam_question.pk)[:9] + str(alternative.pk)[:8],
                'statement': option_text,
                'answer': alternative.is_correct,
            }

    if exam_question.question.category == Question.CLOZE:
        correct_choices = re.findall(r'\[\[(.*?)\]\]', exam_question.question.cloze_content)
        _incorrect = exam_question.question.incorrect_cloze_alternatives.split(',')
        incorrect_choices = [choice.strip() for choice in _incorrect if choice.strip()]

        question['options'] = {
            "type": "select",
            "items": correct_choices + incorrect_choices,
            "incorrect": incorrect_choices,
            "phrase": _format_cloze_question(exam_question.question.cloze_content)
        }

    return question


@app.task(bind=True)
def export_exams_realms(self, exam_pks, client_pk):
    """
    Exporta uma lista de exams para o realms
    """
    client = Client.objects.get(pk=client_pk)

    integration = Integration.objects.filter(
        client=client,
        erp=Integration.REALMS,
    ).first()
    
    total_exams = len(exam_pks)
    errors = []

    for exam_index, _exam in enumerate(exam_pks, 1):
        exam = Exam.objects.get(pk=_exam['exam_id'])

        #Verificando se a prova possui questões sem alternativa correta
        invalid_questions = exam.questions.availables(exam=exam).annotate(
            correct_choices=Count('alternatives', filter=Q(alternatives__is_correct=True))
        ).filter(
            Q(correct_choices=0)
        )

        if invalid_questions.count() > 0:
            errors.append(f'O caderno "{exam.name}" possui {invalid_questions.count()} \
                             questão(es) sem alternativa correta')
            continue

        exam_body = {
            'category_ids': [exam.teaching_stage.code_export if exam.teaching_stage else None],
            'author': integration.username,
            'title': exam.name,
            'shuffle': True,
            'enable_token': True,
        }

        if exam.teaching_stage:
            exam_body['tags'] = [slugify(exam.teaching_stage.name)]

        if exam.id_erp:
            realms_response = realms.update_exam(client, exam, exam_body)
            if error := realms_response.get('errors', False):
                errors.append(str(error))
                continue
        else:
            realms_response = realms.create_exam(client, exam_body)
            if error := realms_response.get('errors', False):
                errors.append(str(error))
                continue
            
            exam.id_erp = realms_response.get('id', None)
            exam.save()

        section_order = 1
        for ets_index, exam_teacher_subject in enumerate(exam.examteachersubject_set.filter(examquestion__isnull=False).using('default').distinct(), 1):
            exam_questions = ExamQuestion.objects.using('default').filter(
                exam_teacher_subject=exam_teacher_subject
            ).availables().annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=[F('exam_teacher_subject__order').asc(), F('order').asc()],
                )
            ).order_by('rank')

            if not exam_questions:
                continue

            section = {
                'key': str(exam_teacher_subject.pk)[:20],
                'type': 'section',
                'order': section_order,
                'section': ets_index,
                'statement': exam_teacher_subject.teacher_subject.subject.name,
            }

            questions_body_create = {'questions': [], 'task_author': integration.username}
            questions_body_update = {'questions': [], 'task_author': integration.username}

            if id_erp := exam_teacher_subject.id_erp:
                section['id'] = id_erp 
                questions_body_update['questions'].append(section)
            else:
                questions_body_create['questions'].append(section)

            for exam_question in exam_questions.filter(id_erp__isnull=True):
                questions_body_create['questions'].append(_mount_question_json(exam_question, client, section_order, ets_index))

            for exam_question in exam_questions.filter(id_erp__isnull=False):
                questions_body_update['questions'].append(_mount_question_json(exam_question, client, section_order, ets_index))
            
            if questions_body_create['questions']:
                response = realms.create_questions_batch(client, exam, questions_body_create)

                if error := response.get('errors', False):
                    errors.append(f'{exam_teacher_subject} | {error}')
                    continue

                for result_question in response['questions']:
                    if result_question['type'] == 'section':
                        exam_teacher_subject.id_erp = result_question['id']
                        exam_teacher_subject.save()
                        continue

                    ExamQuestion.objects.using('default').filter(
                        exam_teacher_subject=exam_teacher_subject,
                        short_code=result_question['key'][:4],
                    ).update(
                        id_erp=result_question['id']
                    )
            
            if questions_body_update['questions']:
                response = realms.update_questions_batch(client, exam, questions_body_update)
                if error := response.get('errors', False):
                    errors.append(f'{exam_teacher_subject} | {error}')
                    continue

            section_order += exam_questions.last().rank + 1

        exam.last_erp_sync = timezone.now()
        exam.save()
        self.update_state(state='PROGRESS', meta={"done": exam_index, "total": total_exams})
    print(errors)
    self.update_state(state=states.SUCCESS, meta={"done": total_exams, "total": total_exams, "errors": len(errors)})

    return True
