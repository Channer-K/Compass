# -*- coding: utf-8 -*-
from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name='ellipses')
def ellipses(value, arg):
    original_string = value
    max_length = arg

    if len(original_string) <= max_length:
        return original_string
    else:
        return original_string[:max_length] + "..."


@register.filter(name='get_due_date_string')
def get_due_date_string(value):
    delta = timezone.now() - value

    if delta.days == 0:
        hours = abs(delta.seconds / 3600)
        if hours == 0:
            return "just now"
        return "about %s %s ago" % (hours, (
            "hour" if hours == 1 else "hours"))
    elif delta.days > 1:
        return "%s %s ago" % (abs(delta.days), (
            "day" if abs(delta.days) == 1 else "days"))


@register.filter(name='can_execute')
def can_execute(subtask, user):

    if not subtask.editable or not subtask.task.editable:
        return False

    ctrl_cls = subtask.get_ctrl_cls()

    if ctrl_cls.can_execute(subtask, user):
        return ctrl_cls

    return False
