from django.conf.urls import patterns, url
from compass import views
from compass import forms

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^signin/$', 'django.contrib.auth.views.login', {
        'template_name': 'auth/signin.html',
        'authentication_form': forms.SigninForm}),
    url(r'^signout/$', 'django.contrib.auth.views.logout_then_login'),
    url(r'^test/$', views.test),
)
