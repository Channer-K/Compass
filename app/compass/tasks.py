# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
from app.celery import app
from compass.conf import settings
from compass.utils.notification import send_email


@app.task
def automatic_dist():
    from compass.models import Task, Subtask
    from compass.utils.helper import get_right_assignee

    tasks = Task.objects.filter(editable=True, available=True)

    for task in tasks:
        progress_id = task.progress_id
        subtask = Subtask.objects.get(pk=progress_id)

        delta = datetime.datetime.now() - subtask.updated_at

        if (delta.total_seconds() / settings.SCHEDULE_PERIOD) >= 1:
            pub_date = datetime.datetime.now() + datetime.timedelta(hours=2)

            subtask.assignee = get_right_assignee()
            subtask.pub_date = pub_date
            subtask.status = subtask.get_next_status()

            subtask.save(update_fields=['assignee', 'pub_date', 'status'])

            subject = u'【新任务】' + "(" + subtask.status.name + ")" + \
                subtask.task.amendment
            contxt = {'applicant': subtask.task.applicant,
                      'at_time': subtask.task.created_at,
                      'task_title': subtask.task.amendment,
                      'version': subtask.task.version
                      }

            send_email.delay(subject=subject,
                             to=[subtask.assignee.email],
                             template_name='schedule',
                             extra_context=contxt)
