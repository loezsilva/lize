from django.contrib import messages
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import redirect

from django.views import defaults

@requires_csrf_token
def page_not_found(request, exception, template_name=None):
    if 'api' in request.get_full_path():
        return defaults.page_not_found(request=request, exception=exception)
    messages.error(request, "Ops! Não conseguimos encontrar o que você está procurando.")
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        return redirect(http_referer)
    return redirect('core:redirect_dashboard')

@requires_csrf_token
def permission_denied(request, exception, template_name=None): 
    if 'api' in request.get_full_path():
        return defaults.permission_denied(request=request, exception=exception)
    messages.error(request, "Permissão negada. Você não tem permissão para acessar esse recurso.")
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        return redirect(http_referer)
    return redirect('core:redirect_dashboard')

@requires_csrf_token
def bad_request(request, exception, template_name=None):
    if 'api' in request.get_full_path():
        return defaults.bad_request(request=request, exception=exception)
    messages.error(request, "A sua requisição não pôde ser processada devido a dados inválidos ou incompletos.")
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        return redirect(http_referer)
    return redirect('core:redirect_dashboard')

@requires_csrf_token
def server_error(request, template_name=None):
    if 'api' in request.get_full_path():
        return defaults.server_error(request=request)
    messages.error(request, "Ocorreu um problema, nossa equipe já foi notificada. Se o erro persistir entre em contato com o suporte.")
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer and 'http' in http_referer:
        return redirect(http_referer)
    return redirect('core:redirect_dashboard')


