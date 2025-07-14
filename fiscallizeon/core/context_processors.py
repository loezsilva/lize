from django.conf import settings


def global_settings(request):
    
    is_mentorizze = 'amentorizze.com.br' in request.META.get('HTTP_HOST', '')
    
    if request.user and request.user.is_authenticated and request.user.user_type == 'student':
        is_mentorizze = request.user.student.client.type_client == 3
    
    return {
        'DEBUG': settings.DEBUG,
        'disable_sleek': True, # adicionado para desativar o sleek em todas as páginas
        'BASE_URL': settings.BASE_URL,
        'ONESIGNAl_APP_ID': settings.ONESIGNAL_APP_ID,
        'IS_MENTORIZZE': is_mentorizze,
        'user_type': request.user.user_type if request.user and request.user.is_authenticated else None,
        'type_client': request.user.get_type_client if request.user and request.user.is_authenticated else None,
    }


def sidebar_active(request):
    """
    Lógica para ajudar a configurar os tópicos ativos na sidebar de coordination
    a lógica não está completa para todos os tópicos.  
    """

    if not request.resolver_match:
        return {
            'application_active': False,
            'application_online_or_homework_active': False,
            'application_presential_or_distribution_active': False,
        }

    url_name = request.resolver_match.url_name

    application_urls = [
        'applications_list',
        'applications_create',
        'applications_create_multiple',
        'applications_update',
        'distribution_list',
        'applications_monitoring',
        'distribution_create',
        'distribution_update',
        'print_applications_list',
    ]
    application_active = url_name in application_urls

    application_online_or_homework_urls = [
        'applications_list',
        'applications_create',
        'applications_update',
    ]
    application_online_or_homework_active = (
        url_name in application_online_or_homework_urls and
        request.GET.get('category') in ['online', 'homework']
    )

    application_presential_or_distribution_urls = [
        'applications_list',
        'applications_create',
        'applications_update',
    ]
    application_presential_or_distribution_active = (
        url_name in application_presential_or_distribution_urls and
        request.GET.get('category') == 'presential'
    )

    management_urls = [
        'classes_list',
        'courses_list',
        'courses_type_list',
        'stage_list',
        'question_tag_list',
        'room_list',
        'room_create',
        'custom-pages-list',
        'exam_header_list',
        'exam_orientations_list',
        'print-configs-list',
        'teaching-stage-list',
        'education-system-list',
        'members_list',
        'partners_list',
        'subjects_list',
        'integration_subject_code_list_create',
        'topic_list',
        'subjects_relation_list',
        'competences_list',
        'abilities_list',
        'inspectors_list',
        'students_list',
        'teachers_list',
        'groups',
        'deviations_list',
        'backgrounds-list',
        'type_application_list',
        'type_application_create',
        'type_application_update',
    ]
    management_active = url_name in management_urls

    exams_urls = [
        'custom-pages-list',
        'exam_header_list',
        'exam_orientations_list',
        'print-configs-list',
        'teaching-stage-list',
        'education-system-list',
        'question_tag_list',
        'deviations_list',
        'backgrounds-list',
        'type_application_list',
        'type_application_create',
        'type_application_update',
    ]
    exam_active = url_name in exams_urls

    return {
        'application_active': application_active,
        'application_online_or_homework_active': application_online_or_homework_active,
        'application_presential_or_distribution_active': application_presential_or_distribution_active,
        "management_active": management_active,
        "exam_active": exam_active,
    }
