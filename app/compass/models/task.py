# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from compass import models as myModels
from django.utils.translation import ugettext_lazy as _


class Task(models.Model):
    applicant = models.ForeignKey(myModels.User)
    version = models.CharField(max_length=32)
    modules = models.ManyToManyField(
        myModels.Module,
        verbose_name=_('modules'),
        help_text=_('The modules will be updated in this task.'))
    created_at = models.DateTimeField(default=timezone.now)
    cause = models.CharField(max_length=128)
    explanation = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    editable = models.BooleanField(default=True)

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
    environment = models.ForeignKey(myModels.Environment)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(max_length=2, blank=True, null=True,
                                      help_text=_('Task status'), default=1)


class Assignment(models.Model):
    subtask = models.ForeignKey(Subtask)
    assignee = models.ForeignKey(myModels.User)


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
    user = models.ForeignKey(myModels.User)
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
