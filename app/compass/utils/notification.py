# -*- coding: utf-8 -*-
from __future__ import absolute_import
from compass.conf import settings
from django.template import Context
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from app.celery import app


@app.task(ignore_result=True)
def send_email(username, subject, from_email=settings.SYSTEM_EMAIL, to=None,
               template_name='default_email_tpl',
               extra_context=None):
        text_tpl = 'email/' + template_name + '.txt'
        html_tpl = 'email/' + template_name + '.html'

        c = Context({
            'username': username
            })

        if extra_context is not None:
            c.update(extra_context)

        text_content = render_to_string(text_tpl, c)
        html_content = render_to_string(html_tpl, c)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, 'text/html')

        msg.send()
