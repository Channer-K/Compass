# -*- coding: utf-8 -*-


def should_audit(user, task):
    if task.available:
        return False

    for module in task.modules():
        role = user.role_in_group(module.group)

        if role.superior:
            return True

    return False


def get_auditors(user, task):
    auditors = set()
    for module in task.modules():
        superior = user.role_in_group(module.group).superior
        if superior:
            auditors.update(role)

    for role in roles:
        if role.superior:
            return True


def audit():
    pass


class Audit(object):
    # create new task
    def get_auditors():
        pass
