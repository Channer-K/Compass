# -*- coding: utf-8 -*-


def can_read_task(user, subtask):
    if not subtask.task in user.get_user_tasks():
        return False

    return True


def tasks_can_access(user):
    """
    Getting the tasks that request user can access

    1. All tasks when request user is superuser
    2. Those whose applicants are request user's subordinates
    3. Those be audited when user in SA.
    4. Only for those that posted by himself

    """
    from compass.models import Task
    tasks = None
    if user.is_superuser:
        tasks = Task.objects.all()
    elif user.is_in_SA:
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
        for group in user.groups.all():
            for module in group.module_set.all():
                modules.add(module)

    return modules
