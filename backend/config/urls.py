"""Project URL configuration; application APIs are intentionally out of scope."""

from django.contrib import admin
from django.urls import path

urlpatterns = [path("admin/", admin.site.urls)]
