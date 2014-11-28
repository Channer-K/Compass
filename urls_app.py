from django.conf.urls import patterns, include, url
from compass.utils.helper import StaticUrls
from django.contrib import admin
admin.autodiscover()

static_urls = StaticUrls()

urlpatterns = patterns('', *static_urls.discover())

urlpatterns += patterns('',
    # Examples:
    # url(r'^$', 'app.views.home', name='home'),
    url(r'^', include('compass.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
