# -*- coding: utf-8 -*-
from compass.utils.helper import httpForbidden
from django.shortcuts import redirect, get_object_or_404


def _check_permission(subtask_id, user):
    from compass.models import Subtask
    subtask = get_object_or_404(Subtask, pk=subtask_id)

    if not can_read_task(user, subtask):
        return False, httpForbidden(403, 'You do not have sufficient '
                                         'permissions to access this page.')

    if not subtask.editable:
        return False, redirect('/history/%s.html' % subtask.url_token)

    return True, subtask


def can_read_task(user, subtask):
    if not subtask.task in user.get_user_tasks():
        return False

    return True


def tasks_can_access(user):
    """
    Getting the tasks that login user has permission to access

    1. User can access his subordinates' tasks when he is a leader in Dev.
    2. User in SA can access those which be verified and qualified.
    3. Those created by themselves are accessible if not meeting above
       conditions.
    """
    from compass.models import Task
    tasks = None
    if user.is_in_SA:
        tasks = Task.objects.all().filter(available=True)
    elif user.is_leader:
        tasks = Task.objects.filter(
            applicant_id__in=[u.pk for u in user.get_subordinate_users()])
    else:
        tasks = Task.objects.filter(applicant=user)

    return tasks


def modules_can_access(user):
    """
    Getting the visitable modules by the way of top-down.
    """
    if user.is_superuser or user.is_in_SA:
        from compass.models import Module
        return Module.objects.all()

    modules = set()

    if user.is_leader:
        for group in user.get_subordinate_groups():
            modules.update(group.module_set.all())
    else:
        for group in user.get_all_groups():
            for module in group.module_set.all():
                modules.add(module)

    return modules
