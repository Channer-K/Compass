# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
from app.celery import app
from compass.conf import settings
from django.conf import settings as djsettings
from compass.utils.notification import send_email


@app.task
def automatic_dist():
    from django.db.models import Q
    from compass.models import Subtask
    w_subtasks = Subtask.objects.filter(
        Q(editable=True),
        Q(assignee__isnull=True),
        Q(status_id=settings.WaitingForPost_Status)
    )

    if w_subtasks:
        from compass.utils.helper import get_right_assignee
        for st in w_subtasks:
            delta = datetime.datetime.now()-st.updated_at

            if (delta.total_seconds() / djsettings.SCHEDULE_PERIOD) >= 1:
                pub_date = datetime.datetime.now()+datetime.timedelta(hours=2)

                st.assignee = get_right_assignee()
                st.pub_date = pub_date
                st.status = st.get_next_status()

                st.save(update_fields=['assignee', 'pub_date', 'status'])

                subject = u'【新任务】'+"("+st.status.name+")"+st.task.amendment
                contxt = {'applicant': st.task.applicant,
                          'at_time': st.task.created_at,
                          'task_title': st.task.amendment,
                          'version': st.task.version
                          }

                send_email.delay(subject=subject,
                                 to=[st.assignee.email],
                                 template_name='schedule',
                                 extra_context=contxt)
