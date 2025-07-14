import math
import string
import random
import os
import re
import requests
import shutil
from django import forms
from typing import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework import pagination
from djangorestframework_camel_case.parser import CamelCaseJSONParser, CamelCaseMultiPartParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from rest_framework.permissions import BasePermission

from django.db import connections
from django.test import TransactionTestCase
from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from django.contrib.postgres.fields import ArrayField
from fiscallizeon.notifications.mixins import NPSMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import get_resolver, reverse, URLResolver, URLPattern, NoReverseMatch

def user_details_after(strategy, details, user=None, *args, **kwargs):
    if not user:
        messages.warning(strategy.request, "Usuário não identificado, acesse com seu usuário e senha padrão.")

def social_user(backend, uid, user=None, *args, **kwargs):
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)

    if social and not user:
        user = social.user

    return {
        "social": social,
        "user": user,
        "is_new": user is None,
        "new_association": social is None,
    }

def associate_user(backend, uid, user=None, social=None, *args, **kwargs):
    if user and not social:
        try:
            social = backend.strategy.storage.user.create_social_auth(
                user, uid, backend.name
            )
        except Exception as err:
            if not backend.strategy.storage.is_integrity_error(err):
                raise
            # Protect for possible race condition, those bastard with FTL
            # clicking capabilities, check issue #131:
            #   https://github.com/omab/django-social-auth/issues/131
            result = social_user(backend, uid, user, *args, **kwargs)
            # Check if matching social auth really exists. In case it does
            # not, the integrity error probably had different cause than
            # existing entry and should not be hidden.
            if not result["social"]:
                raise
            return result
        else:
            return {"social": social, "user": social.user, "new_association": True}

class CheckHasPermission(PermissionRequiredMixin, NPSMixin):
    required_permissions = [settings.COORDINATION, ]
    permission_required = []
    permission_required_any = []
    
    def has_permissions(self):
        user = self.request.user

        return user.user_type in self.required_permissions

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated:
            if not self.has_permissions():
                messages.error(request, "Você não tem permissão para acessar essa página.")
                return redirect('core:redirect_dashboard')
        
            if self.permission_required_any:
                if not any(request.user.has_perm(perm) for perm in self.permission_required_any):
                    raise PermissionDenied
        else:
            raise PermissionDenied
            
        return super(CheckHasPermission, self).dispatch(
            request, *args, **kwargs
        )        
    
class CheckHasPermissionAPI(BasePermission):
    required_permissions = [settings.COORDINATION, ]

    def has_permission(self, request, view):
        
        if request.user.is_authenticated:
            return request.user.user_type in view.required_permissions or request.user.user_type in self.required_permissions

        return False

class NoUnderscoreBeforeNumberCamelCaseJSONParser(CamelCaseJSONParser):
    json_underscoreize = {'no_underscore_before_number': True}

class CamelCaseAPIMixin:
    parser_classes = (CamelCaseJSONParser, CamelCaseMultiPartParser, NoUnderscoreBeforeNumberCamelCaseJSONParser)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    
class ChoiceArrayField(ArrayField):
    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.MultipleChoiceField,
            'choices': self.base_field.choices,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)


def generate_random_string(size=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def generate_random_number(size=6):
    return int(random.random() * 10 ** size)

def _get_client_device(request):
    from fiscallizeon.applications.models import ApplicationStudent

    if request.user_agent.is_mobile:
        return ApplicationStudent.MOBILE
    elif request.user_agent.is_tablet:
        return ApplicationStudent.TABLET
    else:
        return ApplicationStudent.PC


def format_value(value):
    if not value:
        return "-"
    
    number = float(value)
    # if float(value).is_integer():
    #     return int(value)
    return f'{number:.2f}'


def percentage_value(value):
    return f'{format_value(value * 100)}%'


def percentage_formatted(value):
    return f'{format_value(value)}%' if value > 0 else '0%'


def get_task_celery(app, task_name):
    aplication_name = settings.WSGI_APPLICATION.split('.')[0]
    return f"{aplication_name}.{app}.tasks.{task_name}"


class SimpleAPIPagination(pagination.PageNumberPagination):       
    page_size = 20
    display_page_controls = True
    page_size_query_param = 'page_size'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_size', self.get_page_size(self.request)),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


def round_half_up(n, decimals=0):
    expoN = n * 10 ** decimals
    if abs(expoN) - abs(math.floor(expoN)) < 0.5:
        return math.floor(expoN) / 10 ** decimals
    return math.ceil(expoN) / 10 ** decimals


def is_list_of_none(list_of_items):
    return all(i is None for i in list_of_items)

def get_file_from_request(file_url):
    
    with requests.get(file_url, stream=True) as r:
        tmp_file = os.path.join("/tmp/file.csv")

        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

        with open(tmp_file, 'r') as file:
            return file


class CustomTransactionTestCase(TransactionTestCase):
    def _fixture_teardown(self):
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            inhibit_post_migrate = (
                self.available_apps is not None
                or (  # Inhibit the post_migrate signal when using serialized
                    # rollback to avoid trying to recreate the serialized data.
                    self.serialized_rollback
                    and hasattr(connections[db_name], "_test_serialized_contents")
                )
            )
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=db_name,
                reset_sequences=False,
                allow_cascade=True,
                inhibit_post_migrate=inhibit_post_migrate,
            )

def extract_parameters_from_pattern(pattern_str):
    ROUTE_PARAM_REGEX = re.compile(r'<(?:(?P<type>\w+):)?(?P<name>\w+)>')
    return [
        (match.group('name'), match.group('type') or 'str')
        for match in ROUTE_PARAM_REGEX.finditer(pattern_str)
    ]

def get_all_named_patterns(resolver=None, namespace_prefix=''):
    AVAILABLES_NS = [
        'accounts',
        'api',
        'core',
        'applications',
        'students',
        'clients',
        'classes',
        'inspectors',
        'events',
        'answers',
        'questions',
        'subjects',
        'exams',
        'candidates',
        'bncc',
        'omr',
        'notifications',
        'help',
        'diagramations',
        'exports',
        'distribution',
        'materials',
        'integrations',
        'corrections',
        'mentorize',
        'parents',
        'omrnps',
        'weaviatedb',
        'ai',
        'onboarding',
        'dashboards',
        'analytics',
        'app',
    ]
    if resolver is None:
        resolver = get_resolver()

    named = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern) and pattern.name:
            if namespace_prefix in AVAILABLES_NS:
                full_name = f"{namespace_prefix}:{pattern.name}" if namespace_prefix else pattern.name
                named.append((full_name, pattern.pattern.describe()))
        elif isinstance(pattern, URLResolver):
            ns = pattern.namespace
            if ns in AVAILABLES_NS:
                new_prefix = f"{namespace_prefix}:{ns}" if namespace_prefix else ns if ns else namespace_prefix
                named += get_all_named_patterns(pattern, new_prefix)

    return named

def get_reversible_url(name, pattern_str):
    MOCK_VALUES = {
        'int': 1,
        'str': 'mock',
        'slug': 'mock-slug',
        'uuid': '00000000-0000-0000-0000-000000000000',
        'path': 'mock/path',
    }
    params = extract_parameters_from_pattern(pattern_str)
    
    kwargs = {}
    for param_name, param_type in params:
        mock_value = MOCK_VALUES.get(param_type, 'mock')
        kwargs[param_name] = mock_value

    try:
        return reverse(name, kwargs=kwargs)
    except Exception as e:
        print(f"⚠️ Falha ao reverter rota '{name}': {e}")
        return None