from django.conf.urls import patterns, url
from compass import views

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
)
