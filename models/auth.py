# -*- coding: utf-8 -*-
import datetime
from compass.utils import permissions
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib import auth
from django.contrib.auth.models import (
    Group, AbstractBaseUser, Permission, BaseUserManager,)


def update_user_last_login(sender, user, **kwargs):
    """
    A signal receiver which updates the last_login date for
    the user logging out.
    """
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

from django.contrib.auth.models import update_last_login
auth.signals.user_logged_in.disconnect(update_last_login)
auth.signals.user_logged_out.connect(update_user_last_login)


# A few helper functions for common logic to User.
def _user_get_all_permissions(user, obj):
    permissions = set()
    for backend in auth.get_backends():
        if hasattr(backend, "get_all_permissions"):
            permissions.update(backend.get_all_permissions(user, obj))
    return permissions


def _user_has_perm(user, perm, obj):
    for backend in auth.get_backends():
        if hasattr(backend, "has_perm"):
            if backend.has_perm(user, perm, obj):
                return True
    return False


def _user_has_module_perms(user, app_label):
    for backend in auth.get_backends():
        if hasattr(backend, "has_module_perms"):
            if backend.has_module_perms(user, app_label):
                return True
    return False


class Module(models.Model):
    name = models.CharField(max_length=32)
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'compass'


def get_leader_role(self):
    for role in self.role_set.all():
        if role.is_leader:
            return role

    for ancestor in self.get_ancestors(include_self=False).all():
        for role in self.role_set.all():
            if ancestor.is_leader:
                return ancestor

    return None

# Inject to auth.Group
from types import MethodType
models.ForeignKey(
    Group,
    null=True, blank=True,
    related_name='children',
    verbose_name=_('parent'),
    help_text=_('The group\'s parent group. None, if it is a root node.')
).contribute_to_class(Group, 'parent')

Group.get_leader_role = MethodType(get_leader_role, None, Group)

import mptt
mptt.register(Group)


class Role(models.Model):
    name = models.CharField(max_length=64)
    superior = models.ForeignKey('self', blank=True, null=True,
                                 verbose_name=u'汇报对象',
                                 related_name='subordinate_set',
                                 related_query_name='subordinate')
    group = models.ForeignKey(Group,
                              related_name='role_set',
                              related_query_name='role')
    is_leader = models.BooleanField(
        _('leader'), default=False,
        help_text=_('Designates that this role is leader or just staff.'))
    permissions = models.ManyToManyField(
        Permission, blank=True,
        verbose_name=_('permissions'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'compass'


class MyPermissionsMixin(models.Model):
    is_superuser = models.BooleanField(
        _('superuser status'), default=False,
        help_text=_('Designates that this user has all permissions without '
                    'explicitly assigning them.'))
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        help_text=_('Specific groups for this user.'),
        related_name="user_set", related_query_name="user")
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name=_('user permissions'),
        help_text=_('Specific permissions for this user.'),
        related_name="user_set", related_query_name="user")
    roles = models.ManyToManyField(
        Role,
        verbose_name=_('user roles'),
        help_text=_('Specific roles for this user.'),
        related_name='user_set', related_query_name='user')

    class Meta:
        abstract = True

    def get_group_permissions(self, obj=None):
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                permissions.update(backend.get_group_permissions(self, obj))
        return permissions

    def get_role_permissions(self, obj=None):
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_role_permissions"):
                permissions.update(backend.get_role_permissions(self, obj))
        return permissions

    def get_all_permissions(self, obj=None):
        # group permissions and role permissions
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


class MyUserManager(BaseUserManager):

    def _create_user(self, username, email, password,
                     is_staff, is_superuser, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        now = timezone.now()
        if not username:
            raise ValueError('The given username must be set')
        email = MyUserManager.normalize_email(email)
        user = self.model(username=username, email=email,
                          is_staff=is_staff, is_active=True,
                          is_superuser=is_superuser,
                          last_login=now, created_at=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        return self._create_user(username, email, password, False, False,
                                 **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        return self._create_user(username, email, password, True, True,
                                 **extra_fields)


class MyAbstractUser(AbstractBaseUser, MyPermissionsMixin):
    import re
    username = models.CharField(
        _('username'), max_length=30, unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, numbers and '
                    '@/./+/-/_ characters'),
        validators=[validators.RegexValidator(
            re.compile('^[\w.@+-]+$'),
            _('Enter a valid username.'), 'invalid')
        ])
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('email address'))
    is_active = models.BooleanField(
        _('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    is_staff = models.BooleanField(
        _('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    at_work = models.BooleanField(
        _('work status'), default=True,
        help_text=_('Unselect this any tasks won\'t be assigned to you.'))
    created_at = models.DateTimeField(_('date joined'), auto_now_add=True)

    objects = MyUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def __unicode__(self):
        if self.get_full_name():
            return self.get_full_name()
        return self.username

    def get_full_name(self):
        full_name = '%s %s' % (self.last_name, self.first_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    def get_all_groups(self):
        """
        Bottom-up getting all the groups that user belongs to.
        """
        direct_groups = self.groups.all()
        groups = set()

        for group in direct_groups:
            ancestors = group.get_ancestors(include_self=True).all()
            for anc in ancestors:
                groups.add(anc)
            groups.add(group)

        return groups

    def get_subordinate_users(self, include_self=True):
        """
        A word of subordinate is only used when the user is a leader
        instead of a ordinary staff.
        """
        users = set()

        if not self.is_leader:
            return users

        for group in self.get_subordinate_groups(include_self=True):
            users.update(group.user_set.all())

        return users

    def get_subordinate_groups(self, include_self=True):
        groups = set()

        for group in self.groups.all():
            groups.update(group.get_descendants(include_self=include_self))

        return groups

    def get_user_tasks(self):
        return permissions.tasks_can_access(self)

    def get_count_inprogress(self):
        """
        Get the number of subtasks from the users in SA group.
        """
        # not so good
        if not self.is_in_SA:
            return False

        counter = 0
        tasks = permissions.tasks_can_access(self).filter(editable=True)

        for task in tasks:
            counter += task.subtask_set.filter(editable=True).filter(
                assignee=self).count()

        return counter

    def this_week_pub(self):
        date = timezone.now().date()
        start = date - datetime.timedelta(date.weekday())
        end = start + datetime.timedelta(7)
        return self.get_user_tasks().filter(created_at__range=[start, end])

    def last_week_pub(self):
        date = timezone.now().date() - datetime.timedelta(days=7)
        start = date - datetime.timedelta(date.weekday())
        end = start + datetime.timedelta(7)
        return self.get_user_tasks().filter(created_at__range=[start, end])

    def offline(self):
        self.at_work = False
        self.save(update_fields=['at_work'])

    def online(self):
        self.at_work = True
        self.save(update_fields=['at_work'])

    def offline_in_group(self):
        offline_user = set()

        if self.is_leader:
            for user in self.get_subordinate_users():
                if not user.at_work:
                    offline_user.add(user)
        else:
            for group in self.get_all_groups():
                offline_user.update(group.user_set.all().filter(at_work=False))

        return offline_user

    def online_in_group(self):
        online_user = set()

        if self.is_leader:
            for user in self.get_subordinate_users():
                if user.at_work:
                    online_user.add(user)
        else:
            for group in self.get_all_groups():
                online_user.update(group.user_set.all().filter(at_work=True))

        return online_user

    def role_in_group(self, group):
        roles = set()

        for g in group.get_ancestors(include_self=True).all():
            roles.update(g.role_set.all())

        role = list(set(self.roles.all()) & roles)
        if len(role) > 1:
            raise ValueError

        return role[0]

    @property
    def is_leader(self):
        for role in self.roles.all():
            if role.is_leader:
                return True

        return False

    @property
    def is_in_SA(self):
        """ hard coding here """
        SA_GROUP = Group.objects.get(pk=1)

        if SA_GROUP in self.get_all_groups():
            return True

        return False


class User(MyAbstractUser):

    class Meta(MyAbstractUser.Meta):
        app_label = 'compass'
        swappable = 'AUTH_USER_MODEL'
