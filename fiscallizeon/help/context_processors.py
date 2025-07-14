from django.core.cache import cache

from fiscallizeon.help.models import HelpLink, Tutorial
from fiscallizeon.accounts.models import User

def get_help_links(request):
    if request.user.is_anonymous:
        return {
            'help_links': HelpLink.objects.none()
        }

    try:
        url_path = f'{request.resolver_match.namespaces[0]}:{request.resolver_match.url_name}'
    except:
        url_path = ""

    user_type = request.user.user_type
    help_links = cache.get(f'HELPLINKS_{user_type}_{url_path}')

    if not help_links:
        help_links = HelpLink.objects.get_for_path(url_path, user_type)
        cache.set(f'HELPLINKS_{user_type}_{url_path}', help_links, 300)

    return {
        'help_links': help_links
    }

def get_tutoriais(request):
    user: User = request.user
    if not user.is_authenticated:
        return {
            'tutoriais': None
        }

    try:
        url_path = f'{request.resolver_match.namespaces[0]}:{request.resolver_match.url_name}'
    except:
        url_path = ""
    
    user_type = user.user_type
    tutoriais = cache.get(f'TUTORIAIS_{user_type}_{url_path}')

    if not tutoriais:
        tutoriais = Tutorial.objects.get_for_path(url_path, user_type)
        cache.set(f'TUTORIAIS_{user_type}_{url_path}', tutoriais, 300)

    return {
        'tutoriais': tutoriais
    }