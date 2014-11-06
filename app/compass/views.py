# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
from compass.forms import *
from compass.models import *
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


@login_required
def index(request):
    tasks = permissions.tasks_can_access(request.user)
    approvals = tasks.filter(available=False,
                             editable=True,
                             auditor=request.user)

    from django.core.exceptions import ObjectDoesNotExist
    try:
        latest = tasks.filter(available=True).filter(
            editable=True).latest('updated_at')
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

        user = get_object_or_404(User, username=username)

        if user.email != email:
            return httpForbidden(400, 'Bad request.')

        new_password = User.objects.make_random_password()

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
        form = ProfileForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Your profile has been successfully updated!')
            return redirect(profile)
    else:
        form = ProfileForm(
            user=request.user,
            initial={'first_name': request.user.first_name,
                     'last_name': request.user.last_name,
                     'email': request.user.email})
    return render(request, 'others/profile.html', {'form': form})


@ajax_required
@ensure_csrf_cookie
def set_online(request, uid):
    user = User.objects.get(pk=uid)

    if not user.at_work:
        user.online()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@ajax_required
@ensure_csrf_cookie
def set_offline(request, uid):
    user = User.objects.get(pk=uid)

    if user.at_work:
        user.offline()
    return HttpResponse(json.dumps({"status": "ok"}),
                        content_type='application/json')


@login_required
def tasks(request):
    form = FilterForm(request)
    tasks_list = request.user.get_user_tasks()

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(tasks_list, 5)

    page = request.GET.get('page')
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tasks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tasks = paginator.page(paginator.num_pages)

    context = {'form': form, 'tasks': tasks}

    return render(request, 'task/index.html', context)


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
        form = NewTaskForm(request)
        formset = PackagesFormSet()
    return render(request, 'task/new.html', {'form': form,
                                             'form_set': formset})


@login_required
def task_detail(request, tid, sid):
    task = get_object_or_404(Task, pk=tid)

    flag, result = permissions._check_permission(sid, request.user)

    if flag:
        subtask = result
    else:
        return result

    if request.method == 'POST':
        form = ReplyForm(request.POST, request.FILES)
        if form.is_valid():
            reply = Reply(subtask=subtask, user=request.user,
                          subject=request.POST.get('subject'),
                          content=request.POST.get('content'))
            reply.save()

            files = request.FILES.getlist('uploaded_file')
            for afile in files:
                Attachment.objects.create(reply=reply, upload=afile)

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
        form = ReplyForm()

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
    task = get_object_or_404(Task, pk=request.POST.get('tid'))

    from compass.utils.process import FailurePost
    fp_cls = FailurePost(obj=task.in_progress())
    if fp_cls.can_execute(task.in_progress(), user):
        fp_cls.run(request)
        messages.success(request, 'Operation successfully completed.')
    else:
        return httpForbidden(403, 'You do not have sufficient permissions.')

    return redirect(tasks)


@login_required
def filter(request):
    from datetime import datetime

    tasks = permissions.tasks_can_access(request.user)

    from_date = request.POST['from-date']
    to_date = request.POST['to-date']

    f_date, t_date = None, None

    if from_date:
        f_date = datetime.strptime(from_date, "%m/%d/%Y")

    if to_date:
        t_date = datetime.strptime(to_date, "%m/%d/%Y")
    else:
        t_date = datetime.now()

    if f_date and t_date:
        tasks = tasks.filter(created_at__range=(f_date, t_date))

    mids = request.POST.getlist('modules')
    modules = []
    if mids:
        modules.extend(Module.objects.filter(id__in=mids))
    else:
        modules.extend(permissions.modules_can_access(request.user))

    tasks = list(tasks.filter(modules__in=modules))

    sids = request.POST.getlist('status')
    eids = request.POST.getlist('environment')

    sids = sids if sids else StatusControl.objects.all()
    eids = eids if eids else Environment.objects.all()

    for task in tasks:
        is_pop = True
        for s in task.subtask_set.all():
            if (str(s.status.pk) in sids and str(s.environment.pk) in eids):
                is_pop = False
                break

        if is_pop:
            try:
                print task
                tasks.remove(task)
            except ValueError:
                return HttpResponse("Fail")

    print tasks

    return HttpResponse("ok")
