# -*- coding: utf-8 -*-
from django.http import HttpResponseForbidden
from django.template import RequestContext, loader


def wrapHttp403(req, template='403.html'):
    t = loader.get_template(template)
    c = RequestContext(req, {})
    return HttpResponseForbidden(t.render(c))


def ajax_required(f):
    def wrap(request, *args, **kwargs):
            if not request.is_ajax():
                return wrapHttp403(request)
            return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap
