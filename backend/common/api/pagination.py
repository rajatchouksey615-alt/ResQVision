"""Bounded pagination contract for public collections."""

from rest_framework.pagination import LimitOffsetPagination


class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 100
