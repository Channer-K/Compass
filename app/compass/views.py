# -*- coding: utf-8 -*-
from __future__ import absolute_import

from compass import forms, models
from compass.utils import permissions
from compass.utils.helper import httpForbidden
from compass.utils.decorators import ajax_required
from compass.utils.notification import send_email
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import permission_required, login_required
from django.views.decorators.debug import sensitive_post_parameters


def logout(request):
    from django.contrib.auth.views import login
    from django.contrib.auth import logout as auth_logout

    if request.user.is_authenticated():
        auth_logout(request)

    return redirect(login)


@login_required
def index(request):
    tasks = permissions.tasks_can_access(request.user)
    approvals = tasks.filter(available=False,
                             editable=True,
                             auditor=request.user)

    from django.core.exceptions import ObjectDoesNotExist
    try:
        latest = tasks.filter(available=True,
                              editable=True).latest('created_at')
        replies = latest.in_progress().reply_set.all()[:2]
    except ObjectDoesNotExist:
        latest = None
        replies = None

    context = {'latest': latest, 'approvals': approvals,
               'replies': replies}

    return render(request, "index/index.html", context)


def forget_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')

        user = get_object_or_404(models.User, username=username)

        if user.email != email:
            return httpForbidden(400, 'Bad request.')

        new_password = models.User.objects.make_random_password()

        user.set_password(new_password)
        user.save()

        send_email.delay(subject='New Password', to=[user.email],
                         template_name='forget_passwd',
                         extra_context={'new_password': new_password})

        messages.success(request,
                         'Please change your new password just in time.')

        return redirect('/signin/')

    return render(request, 'auth/password_reset.html')


@sensitive_post_parameters()
@login_required
def profile(request):
    if request.method == "POST":
        form = forms.ProfileForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Your profile has been successfully updated!')
            return redirect(profile)
    else:
        form = forms.ProfileForm(
            user=request.user,
            initial={'first_name': request.user.first_name,
                     'last_name': request.user.last_name,
                     'email': request.user.email})
    return render(request, 'others/profile.html', {'form': form})

import json


@ajax_required
@ensure_csrf_cookie
def set_online(request, uid):
    user = models.User.objects.get(pk=uid)

    if not user.at_work:
        user.online()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@ajax_required
@ensure_csrf_cookie
def set_offline(request, uid):
    user = models.User.objects.get(pk=uid)

    if user.at_work:
        user.offline()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@login_required
def tasks(request):
    category = request.GET.get('category')
    page = request.GET.get('page')

    all_tasks = request.user.get_user_tasks()

    if category == 'all':
        task_list = all_tasks
    elif category == 'ongoing':
        sids = [4, 5, 6, 8]
        tids = [t.pk for t in all_tasks if t.in_progress().status.pk in sids]
        task_list = all_tasks.filter(pk__in=tids)
    elif category == 'finished':
        tids = [t.pk for t in all_tasks if not t.in_progress().editable]
        task_list = all_tasks.filter(pk__in=tids)
    else:
        task_list = all_tasks

    # Search Query
    date_from_str, date_to_str = request.GET.get('from'), request.GET.get('to')
    mids = request.GET.getlist('modules')

    import datetime
    if date_from_str:
        f_date = datetime.datetime.strptime(date_from_str, "%m/%d/%Y")
        task_list = task_list.filter(created_at__gte=f_date)

    if date_to_str:
        t_date = datetime.datetime.strptime(date_to_str, "%m/%d/%Y") + \
            datetime.timedelta(days=1) - datetime.timedelta(seconds=1)

        task_list = task_list.filter(created_at__lte=t_date)

    modules = []
    if mids:
        modules.extend(models.Module.objects.filter(id__in=mids))
        task_list = task_list.filter(modules__in=modules)

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(task_list, 5)

    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tasks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tasks = paginator.page(paginator.num_pages)

    form = forms.FilterForm(request, initial={'modules': mids})
    return render(request, 'task/index.html', {'tasks': tasks, 'form': form})


@login_required
@permission_required('compass.add_task', raise_exception=True)
def new_task(request):
    """
    Empty formset forms are required
    """
    from django.forms.formsets import formset_factory, BaseFormSet

    class RequiredFormSet(BaseFormSet):
        def __init__(self, *args, **kwargs):
            super(RequiredFormSet, self).__init__(*args, **kwargs)
            for form in self.forms:
                form.empty_permitted = False
    PackagesFormSet = formset_factory(forms.PackageForm, extra=1, max_num=10,
                                      formset=RequiredFormSet)

    if request.method == 'POST':
        # Bond form and formset
        form = forms.NewTaskForm(request, request.POST)
        formset = PackagesFormSet(request.POST, prefix='form')

        env_list = request.POST.getlist('environment')
        if form.is_valid() and formset.is_valid():
            task = form.save(eids=env_list)
            for f in formset.forms:
                package = f.save(commit=False)
                package.task = task
                package.save()

            """ Send notification if task created successfully """
            scls = task.in_progress().get_ctrl_cls()
            if scls:
                to = None if task.available else [task.auditor.email]
                scls.send_email(request, to=to)

            messages.success(request,
                             'A new task has been created successfully.')

            return redirect(task_detail,
                            tid=task.pk, sid=task.in_progress().pk)
    else:
        form = forms.NewTaskForm(request)
        formset = PackagesFormSet()
    return render(request, 'task/new.html', {'form': form,
                                             'form_set': formset})


@login_required
def task_detail(request, tid, sid):
    task = get_object_or_404(models.Task, pk=tid)

    flag, result = permissions._check_permission(sid, request.user)

    if flag:
        subtask = result
    else:
        return result

    if request.method == 'POST':
        form = forms.ReplyForm(request.POST, request.FILES)
        if form.is_valid():
            reply = models.Reply(subtask=subtask, user=request.user,
                                 subject=request.POST.get('subject'),
                                 content=request.POST.get('content'))
            reply.save()

            files = request.FILES.getlist('uploaded_file')
            for afile in files:
                models.Attachment.objects.create(reply=reply, upload=afile)

            extra_context = {'url': request.build_absolute_uri(),
                             'username': request.user,
                             'at_time': task.created_at,
                             'message': request.POST.get('content')}

            user_list = task.get_stakeholders(exclude=[request.user])

            send_email.delay(subject=u'【新回复】' + task.amendment,
                             to=[user.email for user in user_list],
                             extra_context=extra_context)

            return redirect(task_detail, tid=tid, sid=sid)
    else:
        form = forms.ReplyForm()

    context = {'task': task, 'req_step': subtask, 'form': form}

    ctrl_cls = subtask.get_ctrl_cls()
    if ctrl_cls:
        extra_context = ctrl_cls.extra_context(request)
        if extra_context is not None:
            context.update(extra_context)

    return render(request, 'task/details.html', context)


@login_required
def task_go_next(request):
    if 'sid' not in request.POST:
        return httpForbidden(400, 'Bad request.')

    flag, result = permissions._check_permission(request.POST['sid'],
                                                 request.user)

    if flag:
        subtask = result
    else:
        return result

    subtask.go_run(request)

    return redirect(task_detail, tid=subtask.task.pk, sid=subtask.pk)


@login_required
def task_terminate(request):
    user = request.user
    task = get_object_or_404(models.Task, pk=request.POST.get('tid'))

    from compass.utils.process import FailurePost
    fp_cls = FailurePost(obj=task.in_progress())
    if fp_cls.can_execute(task.in_progress(), user):
        fp_cls.run(request)
        messages.success(request, 'Operation successfully completed.')
    else:
        return httpForbidden(403, 'You do not have sufficient permissions.')

    return redirect(tasks)
