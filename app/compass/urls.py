from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout_then_login
from compass import views
from compass import forms

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^signin/$', login, {
        'template_name': 'auth/signin.html',
        'authentication_form': forms.SigninForm}, name='signin'),
    url(r'^signout/$', logout_then_login, name='signout'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^setOnline/(?P<uid>\d+)$', views.set_online, name='online'),
    url(r'^setOffline/(?P<uid>\d+)$', views.set_offline, name='offline'),
    url(r'^tasks/$', views.tasks, name='tasks'),
    url(r'^filter/$', views.filter, name='filter'),
    url(r'^task/(?P<id>\d+)/step/(?P<step>\d+)$',
        views.task_detail, name='detail'),
    url(r'^task/goNext$', views.task_go_next, name='go-next'),
    url(r'^task/new/$', views.new_task, name='new-task'),
    url(r'^task/terminate/$', views.task_terminate, name='terminate'),
    url(r'^forgetPassword/$', views.forget_password, name='forgetpasswd'),
)
