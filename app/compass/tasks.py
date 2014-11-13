# -*- coding: utf-8 -*-
from __future__ import absolute_import

from datetime import datetime
from app.celery import app
from compass.conf import settings
from compass.views import task_detail
from urlparse import urlparse
from django.core.urlresolvers import reverse
from compass.models import Task, Subtask
from compass.utils.notification import send_email


@app.task
def check_tasks():
    """ hard coding here """
    auditing_tasks = Task.objects.filter(editable=True, available=False)
    planning_subtasks = Subtask.objects.filter(editable=True, status_id=8)
    pub_confirm_subtasks = Subtask.objects.filter(editable=True,
                                                  status_id__in=[5, 6])

    for task in auditing_tasks:
        delta = datetime.now() - task.created_at
        if delta.total_seconds() >= settings.Audit_TimeOut:
            subject = u'【审批任务】' + task.amendment
            url = urlparse(
                "http://" + settings.DOMAIN +
                reverse(task_detail, kwargs={'tid': task.pk,
                                             'sid': task.in_progress().pk})
                )
            contxt = {'url': url.geturl(),
                      'task_title': task.amendment,
                      'version': task.version}

            send_email.delay(subject=subject,
                             to=[task.auditor.email],
                             template_name='audit_timeout',
                             extra_context=contxt)

    for subtask in planning_subtasks:
        delta = subtask.pub_date - datetime.now()
        if (delta.total_seconds() > 60*60 and
                delta.total_seconds() <= settings.Ntf_Before_While_Planning):
            subject = u'【计划发布】' + subtask.task.amendment
        elif delta.total_seconds() <= 60*60:
            subject = u'【任务提醒】' + subtask.task.amendment
            subtask.status = subtask.get_next_status()
            subtask.save(update_fields=['status'])

        url = urlparse("http://" + settings.DOMAIN +
                       reverse(task_detail, kwargs={'tid': subtask.task.pk,
                                                    'sid': subtask.pk})
                       ).geturl()
        contxt = {'at_time': subtask.pub_date, 'url': url,
                  'task_title': subtask.task.amendment,
                  'version': subtask.task.version}

        send_email.delay(subject=subject,
                         to=[subtask.assignee.email],
                         template_name='planning_notify',
                         extra_context=contxt)

    for subtask in pub_confirm_subtasks:
        delta = datetime.now() - subtask.updated_at
        if delta.total_seconds() >= settings.Ntf_Before_While_PandC:
            subject = u'【任务提醒】' + subtask.task.amendment
            url = urlparse("http://" + settings.DOMAIN +
                           reverse(task_detail, kwargs={'tid': subtask.task.pk,
                                                        'sid': subtask.pk}))

            contxt = {'url': url.geturl(),
                      'task_title': subtask.task.amendment,
                      'version': subtask.task.version}
            if subtask.status_id == 5:
                to = [subtask.assignee.email]
            else:
                to = [subtask.task.applicant.email]

            send_email.delay(subject=subject, to=to,
                             template_name='pub_confirm_notify',
                             extra_context=contxt)
