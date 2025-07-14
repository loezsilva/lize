import logging

from django.conf import settings

class LoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if settings.DEBUG:
            return response 

        if request.path in ['/status/']:
            return response

        #namespaces = request.resolver_match.namespaces if request.resolver_match else []
        #avoided_request = 'answers' in namespaces

        if True: #not avoided_request:
            logger = logging.getLogger('fiscallizeon.requests')
            remote_address = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')

            message = f'{request.method} {request.get_full_path()}'

            logger.info(
                message, 
                extra={
                    'remote_address': remote_address,
                    'user': request.user,
                    'user_pk': request.user.pk,
                }
            )
        return response
