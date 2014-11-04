# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
from app.celery import app
from compass.conf import settings
from compass.views import task_detail
from urlparse import urlparse
from django.core.urlresolvers import reverse
from compass.models import Task, Subtask
from compass.utils.notification import send_email


@app.task
def distribute_tasks():
    from compass.utils.helper import get_right_assignee

    tasks = Task.objects.filter(editable=True, available=True)

    for task in tasks:
        subtask = Subtask.objects.get(pk=task.progressing_id)

        delta = datetime.datetime.now() - subtask.updated_at

        if (subtask.status.pk == 4 and
                delta.total_seconds() >= settings.Distribute_After):
            pub_date = datetime.datetime.now() + datetime.timedelta(hours=2)

            subtask.assignee = get_right_assignee()
            subtask.pub_date = pub_date
            subtask.status = subtask.get_next_status()

            subtask.save(update_fields=['assignee', 'pub_date', 'status'])

            subject = u'【新任务】' + "(" + subtask.status.name + ")" + \
                subtask.task.amendment
            url = urlparse("http://" + settings.DOMAIN +
                           reverse(task_detail, kwargs={'tid': subtask.task.pk,
                                                        'sid': subtask.pk})
                           )

            contxt = {'applicant': subtask.task.applicant,
                      'at_time': subtask.task.created_at,
                      'url': url.geturl(),
                      'task_title': subtask.task.amendment,
                      'version': subtask.task.version
                      }

            send_email.delay(subject=subject,
                             to=[subtask.assignee.email],
                             template_name='schedule',
                             extra_context=contxt)


@app.task
def check_tasks():
    """ hard coding here """
    planning_subtasks = Subtask.objects.filter(editable=True, status_id=8)
    pub_confirm_subtasks = Subtask.objects.filter(editable=True,
                                                  status_id__in=[5, 6])

    for subtask in planning_subtasks:
        delta = subtask.pub_date - datetime.datetime.now()
        if delta.total_seconds() <= settings.Ntf_Before_While_Planning:
            subject = u'【提醒】' + subtask.task.amendment
            url = urlparse("http://" + settings.DOMAIN +
                           reverse(task_detail, kwargs={'tid': subtask.task.pk,
                                                        'sid': subtask.pk})
                           )
            contxt = {'at_time': subtask.pub_date,
                      'url': url.geturl(),
                      'task_title': subtask.task.amendment,
                      'version': subtask.task.version}

            send_email.delay(subject=subject,
                             to=[subtask.assignee.email],
                             template_name='planning_notify',
                             extra_context=contxt)

    for subtask in pub_confirm_subtasks:
        delta = datetime.datetime.now() - subtask.updated_at
        if delta.total_seconds() >= settings.Ntf_Before_While_PandC:
            subject = u'【提醒】' + subtask.task.amendment
            url = urlparse("http://" + settings.DOMAIN +
                           reverse(task_detail, kwargs={'tid': subtask.task.pk,
                                                        'sid': subtask.pk})
                           )

            contxt = {'url': url.geturl(),
                      'task_title': subtask.task.amendment,
                      'version': subtask.task.version}
            to = [subtask.assignee.email] if subtask.pk == 5 else [subtask.task.applicant.email]

            send_email.delay(subject=subject,
                             to=to,
                             template_name='pub_confirm_notify',
                             extra_context=contxt)
