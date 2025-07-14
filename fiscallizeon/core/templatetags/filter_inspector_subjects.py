from django import template

register = template.Library()

@register.filter
def filter_inspector_subjects(inspector):
    user = inspector.user 

    if user:
        return user.get_availables_subjects().filter(pk__in=inspector.subjects.filter(teachersubject__active=True))
    return []
