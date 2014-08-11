# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse
from compass.forms import *
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


@login_required
def index(request):
    return render(request, "index.html")


@csrf_exempt
def test(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            return HttpResponse(request.FILES['file'].size)
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


def forget_password(request):
    pass
