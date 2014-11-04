# -*- coding: utf-8 -*-
from compass.utils import process
from compass.conf import settings
from compass.models import User, Module, Environment, Group
from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_save, post_save


class Task(models.Model):
    applicant = models.ForeignKey(User, verbose_name=u'申请人',
                                  related_name="applicant_set",
                                  related_query_name="task_applicant")
    version = models.CharField(u'更新版本', max_length=32)
    modules = models.ManyToManyField(
        Module, verbose_name=u'更新模块',
        help_text=_('The modules will be updated in this task.'))
    amendment = models.CharField(u'变更概述', max_length=128)
    explanation = models.CharField(u'修改说明', max_length=256,
                                   blank=True, null=True)
    comment = models.TextField(u'备注', blank=True, null=True)
    editable = models.BooleanField(default=True)
    auditor = models.ForeignKey(User, verbose_name=u'确认人',
                                related_name='auditor_set',
                                related_query_name='task_auditor',
                                blank=True, null=True)
    available = models.BooleanField(default=False)
    info = models.CharField(max_length=128, blank=True, null=True)
    progressing_id = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'compass'
        ordering = ('-editable', '-created_at',)
        permissions = (
            ("audit_task", "Can audit a task to enable it available"),
            ("distribute_task", "Can distribute a task"),
            ("forcing_close", "Can force to close a task")
        )

    def __unicode__(self):
        return u'%s %s %s' % (
            ", ".join([p.name for p in self.modules.all()]),
            self.version, self.created_at)

    def make_available(self, auditor=None):
        update_fields = ['available']

        if auditor is not None:
            update_fields.append('auditor')
            self.auditor = auditor

        self.available = True
        self.save(update_fields=update_fields)

        for subtask in self.subtask_set.all():
            subtask.status = subtask.status.next
            subtask.save(update_fields=['status'])

        return

    def in_progress(self):
        return self.subtask_set.get(pk=self.progressing_id)

    def next_progressing(self):
        """
        Update the progressing_id to the next. This fun can only be performed
        when status of the current subtask is SuccessPost.
        """
        subtasks = list(self.subtask_set.all())
        curr_idx = subtasks.index(self.in_progress())
        try:
            _next = subtasks[curr_idx+1]
            self.progressing_id = _next.pk
            self.save(update_fields=['progressing_id'])
            return _next
        except IndexError:
            self.editable = False
            self.save(update_fields=['editable'])
            self.subtask_set.filter(editable=True).update(editable=False)

        return

    def get_all_modules(self):
        modules = set()

        for m in self.modules.all():
            modules.add(m)

        return modules

    def get_stakeholders(self, exclude=[]):
        stakeholders = set([self.applicant, self.auditor])

        SA_Group = Group.objects.get(pk=settings.SA_GID)
        SA_Leader = SA_Group.get_leader_role().user_set.all()[0]

        stakeholders.add(SA_Leader)

        if self.in_progress().assignee:
            stakeholders.add(self.in_progress().assignee)

        if exclude:
            stakeholders = stakeholders - set(exclude)

        return stakeholders

    def force_terminate(self, info=None):
        self.editable = False
        update_fields = ['editable']

        if info is not None:
            self.info = info
            update_fields.append('info')

        self.save(update_fields=update_fields)
        try:
            fa = StatusControl.objects.get(pk=settings.FailureAudit_STATUS)
            self.subtask_set.update(editable=False, status=fa)
        except ValueError:
            return

        return


@receiver(pre_save, sender=Task)
def task_pre_save(sender, instance, **kwargs):
    if instance.pk is None:
        return
    old_instance = Task.objects.get(pk=instance.pk)
    if not old_instance.editable:
        raise ValueError("Updating the value of task isn't allowed!")


class StatusControl(models.Model):
    name = models.CharField(max_length=32)
    control_class = models.CharField(max_length=64)
    next = models.ForeignKey('self', blank=True, null=True)
    selected = models.BooleanField(default=False)
    mark = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        app_label = 'compass'


def _subtask_default_status(num=3):
    """ hard coding here! """
    return StatusControl.objects.get(pk=num)


class Subtask(models.Model):
    task = models.ForeignKey(Task)
    environment = models.ForeignKey(Environment)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(StatusControl, default=_subtask_default_status)
    editable = models.BooleanField(default=True)
    info = models.CharField(max_length=128, blank=True, null=True)

    from compass.utils.helper import generate_url_token
    url_token = models.CharField(max_length=128, default=generate_url_token,
                                 blank=True, null=True)
    assignee = models.ForeignKey(User, blank=True, null=True)
    pub_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = 'compass'
        ordering = ('environment__priority',)

    def save(self, *args, **kwargs):
        if 'update_fields' in kwargs:
            kwargs['update_fields'] = list(
                set(list(kwargs['update_fields']) + ['updated_at']))

        return super(Subtask, self).save(*args, **kwargs)

    def get_next_status(self):
        return self.status.next

    def get_curr_status(self):
        return self.status

    def get_ctrl_cls(self):
        str_cls = self.get_curr_status().control_class
        ctrl_cls = getattr(process, str_cls)(obj=self)
        return ctrl_cls

    def go_run(self, request):
        ctrl_cls = self.get_ctrl_cls()
        if ctrl_cls.can_execute(self, request.user):
            ctrl_cls.run(request)
        return

    def generate_snapshot(self, request):
        try:
            self.editable = False
            self.save(update_fields=['editable'])
        except ValueError:
            pass

        context = {'task': self.task, 'req_step': self}

        from django.template import RequestContext
        from django.template.loader import render_to_string
        rendered = render_to_string('task/details.html', context,
                                    context_instance=RequestContext(request))

        from compass.utils.helper import save_snapshot
        save_snapshot(self.url_token, rendered)

    def terminate(self):
        self.task.force_terminate()


@receiver(pre_save, sender=Subtask)
def subtask_pre_save(sender, instance, **kwargs):
    if instance.pk is None:
        return
    old_instance = Subtask.objects.get(pk=instance.pk)
    if not (old_instance.editable and old_instance.task.available):
        raise ValueError("Updating the value of task isn't allowed!")


@receiver(post_save, sender=Subtask)
def subtask_post_save(sender, instance, **kwargs):
    instance.task.save(update_fields=['updated_at'])
    return


class Package(models.Model):
    import re
    from django.core import validators
    filename = models.CharField(u'文件名', max_length=64)
    path = models.CharField(
        u'路径', max_length=128,
        validators=[validators.RegexValidator(
            re.compile('^(ftp|http|\/).*\/$'),
            _('A valid path must start with ftp, http or / and end with /.'),
            'invalid')
        ],
        help_text=_('Full path without filename.'))
    authors = models.CharField(
        u'开发者', max_length=64,
        help_text=_('Multiple authors seperated by commas.'))
    task = models.ForeignKey(Task, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(_('publish status'), default=False)
    comment = models.CharField(u'备注', blank=True, null=True, max_length=256,
                               help_text=_('Change log here.'))

    class Meta:
        app_label = 'compass'

    def __unicode__(self):
        return u'%s -- %s' % (self.authors, self.filename)

    def get_absolute_path(self):
        absolute_path = '%s%s' % (self.path, self.filename)
        return absolute_path.strip()


class Reply(models.Model):
    subtask = models.ForeignKey(Subtask)
    user = models.ForeignKey(User)
    subject = models.CharField(max_length=64)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'compass'
        verbose_name = _('Reply')
        verbose_name_plural = _('Replies')
        ordering = ('-created_at',)


@receiver(post_save, sender=Reply)
def reply_post_save(sender, instance, **kwargs):
    instance.subtask.save(update_fields=['updated_at'])
    return


class Attachment(models.Model):
    reply = models.ForeignKey(Reply)
    upload = models.FileField(upload_to='%Y/%m/%d')

    class Meta:
        app_label = 'compass'

    def __unicode__(self):
        return self.upload.name
