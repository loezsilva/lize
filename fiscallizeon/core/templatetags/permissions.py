from django import template
register = template.Library()

@register.filter
def has_perm(user, permission):    
    return user.has_perm(permission)

@register.filter
def has_module_perms(user, app_label):
    return user.has_module_perms(app_label)