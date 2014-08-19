# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _


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
