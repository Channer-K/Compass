from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout_then_login
from compass import views
from compass import forms

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^signin/$', login, {
        'template_name': 'auth/signin.html',
        'authentication_form': forms.SigninForm}),
    url(r'^signout/$', logout_then_login, name='signout'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^set-online/(?P<uid>\d+)$', views.set_online, name='set-online'),
    url(r'^set-offline/(?P<uid>\d+)$', views.set_offline, name='set-offline'),
    url(r'^tasks/$', views.tasks, name='tasks'),
    url(r'^task/(?P<id>\d+)', views.task_detail, name='detail'),
    url(r'^task/new/$', views.new_task, name='new-task'),
)
