import re
import mammoth

from xml.etree import ElementTree

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from fiscallizeon.core.utils import generate_random_string
from fiscallizeon.core.storage_backends import PublicMediaStorage


def _get_text(raw_text):
    try:       
        return raw_text.split(':', 1)[1]
    except:
        return ''

def _get_list(raw_text):
    try:
        text = _get_text(raw_text).replace(' ', '')
        return text.split(',')
    except:
        return []

def _get_order(raw_order):
    try:
        raw_text = ElementTree.fromstring(raw_order).text
        text = re.sub('[^0-9]','', raw_text)
        return int(text)
    except:
        return 0

def _break_alternatives(raw_alternatives, answer):
    alternatives = []
    raw_alternatives_text = re.sub(r'</?p>', '', raw_alternatives)
    splitted_alternatives_texts = re.split(r'\s*#\w\)', raw_alternatives_text)
    clean_alternatives_texts = list(filter(lambda e: e.strip(), splitted_alternatives_texts))

    for i, clean_alternative_text in enumerate(clean_alternatives_texts):
        
        alternative = {'text': f'<p>{clean_alternative_text}', 'is_correct': False}
        if answer and type(answer) == str:
            try:
                correct_index = 'abcdefghij'.index(answer[0].lower())
                alternative['is_correct'] = correct_index == i
            except:
                alternative['is_correct'] = False
        alternatives.append(alternative)

    return alternatives

def _handle_image(image):
    if settings.DEBUG:
        fs = FileSystemStorage()
    else:
        fs = PublicMediaStorage()

    with image.open() as image_bytes:
        filename = fs.save(generate_random_string(16), image_bytes)
        return {"src": fs.url(filename)}


def get_questions(docx_file):
    questions = []
    result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(_handle_image))
    root = ElementTree.fromstring(f'<html>{result.value}</html>')
    
    for table in root.findall('./table'):
        paragraphs = []
        for td in table.findall('./tr/td'):
            paragraphs.append(
                ''.join(ElementTree.tostring(e, 'unicode') for e in td)
            )

        questions.append(paragraphs)
    
    return questions

def handle_question(question):
    question_data = {}
    question_data['order'] = _get_order(question[0])
    question_data['category'] = _get_text(question[1]).strip().lower()
    question_data['level'] = _get_text(question[2]).strip().lower()
    question_data['abilities'] = _get_list(question[3])
    question_data['enunciation'] = question[4]
    question_data['answer'] = _get_text(question[6]).strip().lower()
    question_data['commented_answer'] = _get_text(question[7])
    question_data['teacher_feedback'] = _get_text(question[8])

    if question_data['category'].lower().strip().startswith('o'):
        question_data['alternatives'] = _break_alternatives(question[5], question_data.get('answer', None))   

    return question_data