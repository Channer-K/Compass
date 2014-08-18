# -*- coding: utf-8 -*-
import re
import mptt

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


class Environment(models.Model):
    name = models.CharField(max_length=64)

    def __unicode__(self):
        return self.name


class ServerGroup(models.Model):
    name = models.CharField(max_length=32)
    environment = models.ForeignKey(Environment)
    comment = models.CharField(max_length=128, null=True, blank=True)
    groups = models.ManyToManyField(Group, verbose_name=_('user groups'))

    class Meta:
        permissions = (
            ('can_view_server_group', 'Can view ServerGroup'),
            )

    def __unicode__(self):
        return u'<%s -- %s>' % (self.name, self.environment)


class Server(models.Model):
    hostname = models.CharField(_('Host name'), max_length=64)
    ip = models.IPAddressField()
    groups = models.ManyToManyField(
        ServerGroup,
        verbose_name=_('server groups'),
        help_text=_('Which groups server in.'))
    is_active = models.BooleanField(default=True)
    comment = models.CharField(max_length=128, null=True, blank=True)

    def __unicode__(self):
        return u'%s -- %s' % (self.hostname, self.ip)

    def offline(self):
        self.is_active = False
        self.save(update_fields=['is_active'])

    def online(self):
        self.is_active = True
        self.save(update_fields=['is_active'])


class Task(models.Model):
    applicant = models.ForeignKey(User)
    version = models.CharField(max_length=32)
    modules = models.ManyToManyField(
        Module,
        verbose_name=_('modules'),
        help_text=_('The modules will be updated in this task.'))
    created_at = models.DateTimeField(default=timezone.now)
    cause = models.CharField(max_length=128)
    explanation = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)
        permissions = (
            ("view_task", "Can see available tasks"),
            ("change_task_status", "Can change the status of tasks"),
            ("close_task", "Can enforce a task to be closed"))

    def __unicode__(self):
        return u'%s %s %s' % (
            ", ".join([p.name for p in self.modules.all()]),
            self.version, self.created_at)


class Subtask(models.Model):
    task = models.ForeignKey(Task)
    pub_date = models.DateTimeField(blank=True, null=True)
    environment = models.ForeignKey(Environment)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(max_length=2, blank=True, null=True,
                                      help_text=_('Task status'), default=1)


class Assignment(models.Model):
    subtask = models.ForeignKey(Subtask)
    assignee = models.ForeignKey(User)


class Package(models.Model):
    filename = models.CharField(max_length=64)
    path = models.CharField(max_length=256)
    authors = models.CharField(
        max_length=64, verbose_name=_('authors'),
        help_text=_('The authors of package. '
                    'Multiple authors are separated with comma.'))
    task = models.ForeignKey(Task, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(_('publish status'), default=False)
    comment = models.TextField(blank=True, null=True,
                               help_text=_('Change log here.'))

    def __unicode__(self):
        return u'%s -- %s' % (self.authors, self.filename)

    def get_absolute_path(self):
        absolute_path = '%s/%s' % (self.path, self.filename)
        return absolute_path.strip()


class Reply(models.Model):
    subtask = models.ForeignKey(Subtask)
    user = models.ForeignKey(User)
    subject = models.CharField(max_length=64)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Reply')
        verbose_name_plural = _('Replies')
        ordering = ('created_at',)


class Attachment(models.Model):
    reply = models.ForeignKey(Reply)
    upload = models.FileField(upload_to='%Y/%m/%d')
