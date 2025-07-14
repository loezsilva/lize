from django import template
register = template.Library()

@register.filter
def get_parent_user(student, parent_email):
    return student.parent_set.filter(email=parent_email, user__isnull=False)