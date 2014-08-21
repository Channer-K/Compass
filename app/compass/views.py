# -*- coding: utf-8 -*-
import json
from compass.forms import *
from compass.models import *
from compass.helper import ajax_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.debug import sensitive_post_parameters
from django.forms.formsets import formset_factory, BaseFormSet


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
        form = NewTaskForm()
    return render(request, 'upload.html', {'form': form})


def forget_password(request):
    pass


@sensitive_post_parameters()
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


@login_required
def new_task(request):
    # This class is used to make empty formset forms required
    class RequiredFormSet(BaseFormSet):
        def __init__(self, *args, **kwargs):
            super(RequiredFormSet, self).__init__(*args, **kwargs)
            for form in self.forms:
                form.empty_permitted = False
    PackagesFormSet = formset_factory(PackageForm, extra=1, max_num=10,
                                      formset=RequiredFormSet)
    if request.method == 'POST':
        # Bond form and formset
        form = NewTaskForm(request, request.POST)
        formset = PackagesFormSet(request.POST, prefix='form')

        env_list = request.POST.getlist('environment')
        if form.is_valid() and formset.is_valid():
            task = form.save(eids=env_list)
            for f in formset.forms:
                package = f.save(commit=False)
                package.task = task
                package.save()
            return HttpResponse('ok')
    else:
        form = NewTaskForm(request)
        formset = PackagesFormSet()
    return render(request, 'task/new.html', {'form': form,
                                             'form_set': formset})


def task_detail(request, id=None):
    # task = Subtask.objects.filter(task_id=id)
    task = get_object_or_404(Task, pk=id)
    return render(request, 'task/details.html')
