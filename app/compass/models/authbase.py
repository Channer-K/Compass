# -*- coding: utf-8 -*-
from django.core.mail import send_mail
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib import auth
from django.contrib.auth.models import (
    Group, AbstractBaseUser, Permission, BaseUserManager,)

TASK_STATUS = (
    (-2, u'审核失败'),
    (-1, u'发布失败'),
    (0, u'发布成功'),
    (1, u'等待审核'),
    (1, u'等待发布'),
    (2, u'发布中'),
    (3, u'等待确认'),
)

TASK_ACTIONS = (
    (-3, u'强制终止'),   # read-only
    (-2, u'任务失败'),   # read-only
    (-1, u'拒绝发布'),   # read-only
    (0, u'审核通过'),
    (1, u'接受'),
    (2, u'拒绝'),
    (3, u'完成'),
    (4, u'确认'),
)


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


# A few helper functions for common logic between User and AnonymousUser.
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

    def __unicode__(self):
        return self.name


# Inject some fields to auth.Group
models.ForeignKey(
    Group,
    null=True, blank=True,
    related_name='children',
    verbose_name=_('parent'),
    help_text=_('The group\'s parent group. None, if it is a root node.')
    ).contribute_to_class(Group, 'parent')

models.ManyToManyField(
    Module,
    null=True, blank=True,
    verbose_name=_('modules')).contribute_to_class(Group, 'modules')

import mptt
mptt.register(Group)


class Role(models.Model):
    name = models.CharField(max_length=64)
    report_to = models.ForeignKey('self', blank=True, null=True,
                                  verbose_name=_('Report object'))
    group = models.ForeignKey(Group)
    permissions = models.ManyToManyField(
        Permission, blank=True,
        verbose_name=_('permissions'))

    def __unicode__(self):
        return self.name


class MyPermissionsMixin(models.Model):
    groups = models.ManyToManyField(
        Group,
        blank=True,
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
        blank=True,
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
    def _create_user(self, username, email, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        now = timezone.now()
        if not username:
            raise ValueError('The given username must be set')
        email = MyUserManager.normalize_email(email)
        user = self.model(username=username, email=email,
                          last_login=now, created_at=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        admin_group = Group.objects.get_or_create(name='administrator')[0]
        admin_role = Role.objects.get_or_create(name='administrator',
                                                group=admin_group)[0]
        admin = self._create_user(username, email, password, **extra_fields)
        admin.roles.add(admin_role)
        admin.groups.add(admin_group)
        return admin


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
    at_work = models.BooleanField(
        _('work status'), default=True,
        help_text=_('You won\'t receive any tasks when is checked.'))
    created_at = models.DateTimeField(_('date joined'), auto_now_add=True)

    objects = MyUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True
        permissions = (
            ('can_view_users', 'Can view users'),
            )

    def __unicode__(self):
        return self.username

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """ Sends an email to this User. """
        send_mail(subject, message, from_email, [self.email])

    def get_all_groups(self):
        direct_groups = self.groups.all()
        groups = set()

        for group in direct_groups:
            ancestors = group.get_ancestors().all()
            for anc in ancestors:
                groups.add(anc)
            groups.add(group)

        return groups

    def get_all_roles(self):
        roles = set()

        for role in self.roles.all():
            roles.add(role)

        return roles

    def all_modules_choices(self):
        groups = self.groups.all()
        modules = set()

        for group in groups:
            for module in group.modules.all().values_list('id', 'name'):
                modules.add(module)

        modules_sorted = list(modules)
        modules_sorted.sort()
        return modules_sorted

    def offline(self):
        self.at_work = False
        self.save(update_fields=['at_work'])

    def online(self):
        self.at_work = True
        self.save(update_fields=['at_work'])

    def offline_in_group(self):
        offline_user = set()
        for group in self.groups.all():
            for user in group.user_set.all():
                if not user.at_work:
                    offline_user.add(user.username)
        return (" ").join(offline_user)

    def online_in_group(self):
        online_user = set()
        for group in self.groups.all():
            for user in group.user_set.all():
                if user.at_work:
                    online_user.add(user.username)
        return (" ").join(online_user)

    @property
    def is_superuser(self):
        if self.roles.filter(name='administrator') or \
           self.groups.filter(name='administrator'):
            return True
        return False

    @property
    def is_staff(self):
        return self.is_superuser


class User(MyAbstractUser):
    class Meta(MyAbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
