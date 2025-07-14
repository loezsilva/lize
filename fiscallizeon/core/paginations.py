from rest_framework.pagination import LimitOffsetPagination


class LimitOffsetPagination(LimitOffsetPagination):
    max_limit = 300
    default_limit = 50