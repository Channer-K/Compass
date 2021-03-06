from django.conf.urls import patterns, url
from django.contrib.auth.views import login
from compass import views
from compass import forms

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^signin/$', login, {
        'template_name': 'auth/signin.html',
        'authentication_form': forms.SigninForm}, name='signin'),
    url(r'^signout/$', views.signout, name='signout'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^setOnline/(?P<uid>\d+)$', views.set_online, name='online'),
    url(r'^setOffline/(?P<uid>\d+)$', views.set_offline, name='offline'),
    url(r'^tasks/$', views.tasks, name='tasks'),
    url(r'^task/(?P<tid>\d+)/step/(?P<sid>\d+)$',
        views.task_detail, name='detail'),
    url(r'^task/go-next$', views.task_go_next, name='go-next'),
    url(r'^task/new/$', views.new_task, name='new-task'),
    url(r'^task/terminate/$', views.task_terminate, name='terminate'),
    url(r'^forgetPassword/$', views.forget_password, name='forgetpasswd'),
)
