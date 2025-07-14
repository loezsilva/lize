from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import OptionAnswer

def get_answer_object(application_student, question):
    
    answer_object = {
        'answer_id': None,
        'text': None,
        'file_url': None,
        'checked_options': []
    }
    
    if question.category == Question.CHOICE:
        if answer := application_student.option_answers.select_related('question_option').filter(status=OptionAnswer.ACTIVE, question_option__question=question).first():
            answer_object['answer_id'] = str(answer.id)
            answer_object['checked_options'] = [answer.question_option.id]
    
    if question.category == Question.SUM_QUESTION:
        if answer := application_student.sum_answers.select_related('question').filter(question=question).first():
            answer_object['answer_id'] = str(answer.id)
            answer_object['checked_options'] = answer.question_options.values_list('id', flat=True)
    
    if question.category == Question.TEXTUAL:
        if answer := application_student.textual_answers.select_related('question').filter(question=question).first():
            answer_object['answer_id'] = str(answer.id)
            answer_object['text'] = answer.content
            
    if question.category == Question.FILE:
        if answer := application_student.file_answers.select_related('question').filter(question=question).first():
            answer_object['answer_id'] = str(answer.id)
            answer_object['file_url'] = answer.arquivo.url if answer.arquivo else None
    
    return answer_object