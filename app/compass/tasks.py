# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
from app.celery import app
from compass.conf import settings
from django.template import Context
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


@app.task(ignore_result=True)
def send_email(subject, from_email=settings.SYSTEM_EMAIL, to=None,
               template_name='default_email_tpl',
               extra_context=None):
        text_tpl = 'email/' + template_name + '.txt'
        html_tpl = 'email/' + template_name + '.html'

        c = {}

        if extra_context is not None:
            c.update(extra_context)

        text_content = render_to_string(text_tpl, Context(c))
        html_content = render_to_string(html_tpl, Context(c))

        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, 'text/html')

        msg.send()


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

            if (delta.total_seconds() / 60) >= 1:
                pub_date = datetime.datetime.now()+datetime.timedelta(hours=2)

                st.assignee = get_right_assignee()
                st.pub_date = pub_date
                st.status = st.get_next_status()

                st.save(update_fields=['assignee', 'pub_date', 'status'])
