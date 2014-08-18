# -*- coding: utf-8 -*-
import json
from compass.forms import *
from compass.models import *
from compass.helper import ajax_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


@login_required
def index(request):
    return render(request, "index/index.html")


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


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated successfully!')
            return redirect(profile)
    else:
        form = ProfileForm(
            user=request.user,
            initial={'first_name': request.user.first_name,
                     'last_name': request.user.last_name,
                     'email': request.user.email})
    return render(request, 'others/profile.html', {'form': form})


@csrf_exempt
@ajax_required
def set_online(request, uid):
    user = User.objects.get(pk=uid)

    if not user.at_work:
        user.online()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@csrf_exempt
@ajax_required
def set_offline(request, uid):
    user = User.objects.get(pk=uid)

    if user.at_work:
        user.offline()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@login_required
def tasks(request):
    form = FilterForm(request.user)
    return render(request, 'task/index.html', {'form': form})


def task_detail(request, id=None):
    # task = Subtask.objects.filter(task_id=id)
    return render(request, 'task/details.html')
