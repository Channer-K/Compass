# -*- coding: utf-8 -*-
from django.http import HttpResponse


def index(request):
    if request.user.has_perm('compass.add_role'):
        return HttpResponse('Niubi')
    return HttpResponse('Hello World...')
