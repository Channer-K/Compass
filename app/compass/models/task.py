# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from compass.models import User, Module, Environment
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_save


class Task(models.Model):
    applicant = models.ForeignKey(User,
                                  verbose_name=u'申请人',
                                  related_name="applicant_set",
                                  related_query_name="applicant_task")
    version = models.CharField(u'更新版本', max_length=32)
    modules = models.ManyToManyField(
        Module, verbose_name=u'更新模块',
        help_text=_('The modules will be updated in this task.'))
    created_at = models.DateTimeField(default=timezone.now)
    amendment = models.CharField(u'变更内容', max_length=128)
    explanation = models.CharField(u'修改说明', max_length=128,
                                   blank=True, null=True)
    comment = models.TextField(u'备注', blank=True, null=True)
    editable = models.BooleanField(default=True)
    available = models.BooleanField(default=False)
    info = models.CharField(max_length=128, blank=True, null=True)
    progressing_id = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        app_label = 'compass'
        ordering = ('-created_at',)
        permissions = (
            ("view_task", "Can browse the tasks"),
            ("available_task", "Can verify tasks"),
            ("close_task", "Can set tasks read-only"))

    def __unicode__(self):
        return u'%s %s %s' % (
            ", ".join([p.name for p in self.modules.all()]),
            self.version, self.created_at)

    def progressing(self):
        return Subtask.objects.filter(task=self).get(pk=self.progressing_id)


def task_pre_save(sender, **kwargs):
    obj = kwargs['instance']
    if not obj.editable:
            raise ValueError("Updating the value of task isn't allowed!")
pre_save.connect(task_pre_save, sender=Task)


class Subtask(models.Model):
    task = models.ForeignKey(Task)
    pub_date = models.DateTimeField(blank=True, null=True)
    environment = models.ForeignKey(Environment)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(max_length=2, blank=True, null=True,
                                      help_text=_('Task status'), default=1)
    editable = models.BooleanField(default=True)
    info = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        app_label = 'compass'
        ordering = ('pk', 'environment',)


def subtask_pre_save(sender, **kwargs):
    obj = kwargs['instance']
    if obj.editable:
            raise ValueError("Updating the value of task isn't allowed!")
pre_save.connect(task_pre_save, sender=Subtask)


class Assignment(models.Model):
    subtask = models.ForeignKey(Subtask)
    assignee = models.ForeignKey(User)

    class Meta:
        app_label = 'compass'


class Package(models.Model):
    filename = models.CharField(u'文件名', max_length=64)
    path = models.CharField(u'路径', max_length=256,
                            help_text=_('Full path without filename from path'
                                        ' that includes filename.'))
    authors = models.CharField(u'开发者', max_length=64,
                               help_text=_('Use commas to separate authors.'))
    task = models.ForeignKey(Task, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(_('publish status'), default=False)
    comment = models.TextField(u'备注', blank=True, null=True,
                               help_text=_('Change log here.'))

    class Meta:
        app_label = 'compass'

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
        app_label = 'compass'
        verbose_name = _('Reply')
        verbose_name_plural = _('Replies')
        ordering = ('created_at',)


class Attachment(models.Model):
    reply = models.ForeignKey(Reply)
    upload = models.FileField(upload_to='%Y/%m/%d')

    class Meta:
        app_label = 'compass'
