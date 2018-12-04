from django.conf.urls import url

from . import views

app_name="nanotask"
urlpatterns = [
    url(r'^base/(?P<project_name>\w+)/$', views.load_base, name="load_base"),
    url(r'^nanotask/(?P<project_name>\w+)/$', views.load_nanotask, name="load_nanotask"),
    url(r'^nanotask/(?P<project_name>\w+)/(?P<template_name>\w+)/$', views.load_static_template,
        name="load_static_template"),
    url(r'^answer/save/$', views.save_answer, name="save_answer"),
    url(r'^assignment/save/$', views.save_assignment, name="save_assignment")
]

#    url(r'^create_nanotask/(?P<project_name>\w+)/(?P<template_name>\w+)/$', views.create_nanotask),
