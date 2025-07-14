from django import template
from fiscallizeon.exams.models import Wrong
register = template.Library()

@register.filter
def get_opened_student_wrongs(student):
    wrongs = Wrong.objects.filter(
        student=student,
        status=Wrong.AWAITING_REVIEW
    )
    return wrongs.count() if wrongs else 0