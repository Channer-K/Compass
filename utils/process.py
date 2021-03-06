# -*- coding: utf-8 -*-
from datetime import datetime
from compass.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import get_object_or_404
from compass.utils.notification import send_email as send_queue
from compass.utils.helper import httpForbidden

TPL_PATH = 'task/operate/'


class TaskProcessingBase(object):

    """ Base class """

    def __init__(self, obj=None):
        self.obj = obj
        self.task = self.obj.task
        self.render_id = '%s_%s' % ('sub', self.obj.pk)

    def run(self, request):
        _next_status = self.obj.status.next
        self.obj.status = _next_status
        self.obj.save(update_fields=['status'])

        if self.obj.status.next is None:
            self.obj.generate_snapshot(request)

        return

    def can_execute(self, subtask, user):
        return False

    def extra_context(self, requset):
        return None

    def send_mail(self, request,
                  subject=None, to=None,
                  template_name='default_email_tpl',
                  extra_context=None):

        if subject is None:
            subject = u'【更新】' + self.task.amendment

        if to is None:
            to = [self.task.applicant.email]

        from urlparse import urlparse
        from compass.views import task_detail
        from django.core.urlresolvers import reverse

        # re-read the new value from database
        from compass.models import Subtask
        subtask = Subtask.objects.get(pk=self.obj.pk)

        if subtask.editable:
            url = urlparse("http://" + settings.DOMAIN + reverse(
                task_detail, kwargs={'tid': self.task.pk, 'sid': self.obj.pk})
            ).geturl()
        else:
            url = urlparse("http://" + settings.DOMAIN + "/history/" +
                           self.obj.url_token + ".html").geturl()

        ctx = {
            'url': url,
            'at_time': self.task.updated_at.strftime("%Y-%m-%d %I:%M%p"),
            'username': self.task.applicant
        }

        if extra_context is not None:
            ctx.update(extra_context)

        send_queue.delay(subject=subject, to=to, template_name=template_name,
                         extra_context=ctx)

    @property
    def template(self):
        template_name = TPL_PATH + '_default.html'
        return template_name


class FailureAudit(TaskProcessingBase):

    """ 审核失败 """

    def get_status_in_failure(self):
        from compass.models import StatusControl
        return StatusControl.objects.get(pk=1)

    def run(self, request):
        from compass.models import StatusControl
        failAudit = StatusControl.objects.get(pk=1)
        self.task.subtask_set.update(status=failAudit)

        self.task.force_terminate(request.POST['info'])

        for subtask in self.task.subtask_set.all():
            subtask.generate_snapshot(request)

        """ Notify applicant """
        self.send_email(request)

        return

    def send_email(self, request):
        subject = u'【驳回】' + self.task.amendment
        template_name = 'reject'
        extra_context = {'username': self.task.auditor,
                         'task_title': self.task.amendment,
                         'info': self.task.info, 'version': self.task.version}

        super(FailureAudit, self).send_mail(request, subject=subject,
                                            template_name=template_name,
                                            extra_context=extra_context)


class FailurePost(TaskProcessingBase):

    """ 发布失败 """

    def can_execute(self, subtask, user):
        if (user.has_perm('compass.forcing_close') or
                self.obj.assignee == user):
            return True

        return False

    def run(self, request):
        from compass.models import StatusControl
        failurePost = StatusControl.objects.get(pk=2)
        self.task.subtask_set.update(status=failurePost)

        self.task.force_terminate(request.POST['info'])

        for subtask in self.task.subtask_set.all():
            subtask.generate_snapshot(request)

        self.send_email(request)
        return

    def send_email(self, request):
        subject = u'【失败】' + self.task.amendment
        to = [user.email for user in self.task.get_stakeholders()]

        if self.obj.assignee is not None:
            to.append(self.obj.assignee.email)

        template_name = 'fail'
        extra_context = {'info': self.task.info,
                         'task_title': self.task.amendment,
                         'version': self.task.version}

        super(FailurePost, self).send_mail(request, subject=subject, to=to,
                                           template_name=template_name,
                                           extra_context=extra_context)


class WaitingForAudit(TaskProcessingBase):

    """ 等待审核 """

    def can_execute(self, subtask, user):
        if (user.has_perm('compass.audit_task') and self.task.auditor == user):
            return True

        return False

    def approval(self, request):
        user = request.user

        for role in user.roles.all():
            if role.superior:
                user_set = role.superior.user_set.all()
                self.task.auditor = user_set[0]
                self.task.save(update_fields=['auditor'])

                self.send_email(request, to=[user_set[0].email])
                return

        self.task.make_available(auditor=user)

        # re-read the subtask status from database
        from compass.models import Subtask
        st = Subtask.objects.get(pk=self.obj.pk)
        scls = st.get_ctrl_cls()

        if scls:
            scls.send_email(request)
        return

    def decline(self, request):
        # Call for run() of FailureAudit
        FailureAudit(obj=self.obj).run(request)
        return

    def run(self, request):
        opt = request.POST.get('opt')

        if opt is None:
            return httpForbidden(400, 'Bad request.')

        if opt == 'approval':
            self.approval(request)
        elif opt == 'decline':
            self.decline(request)
        return

    def send_email(self, request, to=None):
        subject = u'【待审核】' + self.task.amendment
        template_name = 'w_audit'
        extra_context = {'task_title': self.task.amendment,
                         'version': self.task.version}

        super(WaitingForAudit, self).send_mail(request,
                                               subject=subject, to=to,
                                               template_name=template_name,
                                               extra_context=extra_context)

    @property
    def template(self):
        template_name = TPL_PATH + '_waitingforaudit.html'
        return template_name


class SuccessPost(TaskProcessingBase):

    """ 发布成功 """

    def run(self, request):
        super(SuccessPost, self).run(request)

        self.send_email(request)
        return

    def send_email(self, request):
        subject = u'【成功】' + self.task.amendment
        template_name = 'success'

        to = [user.email for user in self.task.get_stakeholders()]

        extra_context = {'task_title': self.task.amendment,
                         'version': self.task.version}

        super(SuccessPost, self).send_mail(request, subject=subject, to=to,
                                           template_name=template_name,
                                           extra_context=extra_context)


class WaitingForPost(TaskProcessingBase):

    """ 等待发布 """

    def can_execute(self, subtask, user):
        if (user.has_perm('compass.distribute_task') or
                user == self.obj.assignee):
            return True

        return False

    def run(self, request):
        opt = request.POST.get('opt')

        if opt is None:
            return httpForbidden(400, 'Bad request.')

        from compass.models import User, Subtask, StatusControl
        if opt == 'dist':
            subtask_list = request.POST.getlist('subtask')
            pub_user = request.POST.getlist('pub_user')
            date_list = request.POST.getlist('pub_date')

            for idx, date in enumerate(date_list):
                if date == '':
                    continue

                subtask = get_object_or_404(Subtask, pk=subtask_list[idx])
                assignee = get_object_or_404(User, pk=pub_user[idx])

                subtask.assignee = assignee

                update_fields = ['assignee', 'pub_date']

                pub_date = datetime.strptime(date_list[idx], '%m/%d/%Y %H')
                subtask.pub_date = pub_date
                delta = pub_date - timezone.now()

                if subtask == subtask.task.in_progress():
                    if (delta.total_seconds() / 3600) >= 6:
                        """ hard coding here """
                        planning_status = StatusControl.objects.get(pk=8)
                        subtask.status = planning_status
                    else:
                        subtask.status = subtask.get_next_status()

                    update_fields.append('status')

                subtask.save(update_fields=update_fields)

                scls = subtask.get_ctrl_cls()
                if scls:
                    scls.send_email(request)

        return

    def extra_context(self, request):
        pub_tasks = self.task.subtask_set.filter(status_id=4)
        from compass.utils.helper import get_all_online_SAs
        pub_users = get_all_online_SAs()

        return {'pub_tasks': pub_tasks, 'pub_users': pub_users}

    def send_email(self, request, to=None):
        subject = u'【发布任务】' + self.task.amendment
        template_name = 'new_task'

        recipients = self.task.get_stakeholders(exclude=[self.task.applicant,
                                                         self.task.auditor])

        to = [user.email for user in recipients]

        extra_context = {'task_title': self.task.amendment,
                         'version': self.task.version}

        super(WaitingForPost, self).send_mail(request, subject=subject, to=to,
                                              template_name=template_name,
                                              extra_context=extra_context)

    @property
    def template(self):
        template_name = TPL_PATH + '_waitingforpub.html'
        return template_name


class Planning(TaskProcessingBase):

    """ 计划发布 """

    def can_execute(self, subtask, user):
        if (user.is_in_SA and user.is_leader) or self.obj.assignee == user:
            return True

        return False

    def run(self, request):
        new_pdate = request.POST.get('pub_date')

        if new_pdate:
            new_pdate = datetime.strptime(new_pdate, '%m/%d/%Y %H')

            if new_pdate <= timezone.now():
                return

            self.obj.pub_date = new_pdate
            self.obj.save(update_fields=['pub_date'])
            messages.success(request,
                             'Publish date has been updated successfully!')

            self.send_email(request)
        else:
            """ Publish current task instantly. """
            super(Planning, self).run(request)

            self.obj.pub_date = timezone.now().strftime('%Y-%m-%d %H:00:00')
            self.obj.save(update_fields=['pub_date'])

            if self.obj.assignee == request.user:
                messages.success(request, 'Publish date has been updated '
                                          'successfully! Please start a '
                                          'publishing as soon as possible.')
            else:
                messages.info(request, 'We have informed related publisher and'
                                       ' the task will be published in a short'
                                       ' time.')

            # re-read the subtask status from database
            from compass.models import Subtask
            st = Subtask.objects.get(pk=self.obj.pk)
            scls = st.get_ctrl_cls()

            if scls:
                scls.send_email(request)

        return

    def send_email(self, request):
        template_name = 'planning'
        subject = u'【计划发布】' + self.task.amendment

        to = [user.email for user in self.task.get_stakeholders()]

        extra_context = {
            'username': self.obj.assignee,
            'at_time': self.obj.pub_date.strftime("%Y-%m-%d %I:%M%p"),
            'task_title': self.task.amendment,
            'version': self.task.version
        }

        super(Planning, self).send_mail(request, subject=subject, to=to,
                                        template_name=template_name,
                                        extra_context=extra_context)

    @property
    def template(self):
        template_name = TPL_PATH + '_planning.html'
        return template_name


class Posting(TaskProcessingBase):

    """ 发布中 """

    def can_execute(self, subtask, user):
        if user.is_in_SA and user == self.obj.assignee:
            return True

        return False

    def run(self, request):
        opt = request.POST.get('opt')

        if opt == 'finish':
            super(Posting, self).run(request)

            # re-read the subtask status from database
            from compass.models import Subtask
            st = Subtask.objects.get(pk=self.obj.pk)
            scls = st.get_ctrl_cls()

            if scls:
                scls.send_email(request)

            messages.success(
                request,
                'Please waiting a successful confirmation from the developer.')
        else:
            return httpForbidden(400, 'Bad request.')
        return

    def send_email(self, request):
        template_name = 'posting'
        subject = u'【正在发布】' + self.task.amendment

        to = [user.email for user in self.task.get_stakeholders()]

        extra_context = {
            'username': self.obj.assignee,
            'at_time': self.obj.pub_date.strftime("%Y-%m-%d %I:%M%p"),
            'task_title': self.task.amendment,
            'version': self.task.version
            }

        super(Posting, self).send_mail(request, subject=subject, to=to,
                                       template_name=template_name,
                                       extra_context=extra_context)

    @property
    def template(self):
        template_name = TPL_PATH + '_posting.html'
        return template_name


class Confirmation(TaskProcessingBase):

    """ 等待确认 """

    def can_execute(self, subtask, user):
        if user == self.task.applicant or user == subtask.assignee:
            return True

        return False

    def run(self, request):
        opt = request.POST.get('opt')

        if opt == 'yes':
            SuccessPost(obj=self.obj).run(request)
            self.task.next_progressing()
        elif opt == 'no':
            FailurePost(obj=self.obj).run(request)

        return

    def send_email(self, request):
        subject = u'【待确认】' + self.task.amendment
        template_name = 'confirmation'

        extra_context = {'task_title': self.task.amendment,
                         'version': self.task.version}

        super(Confirmation, self).send_mail(request, subject=subject,
                                            template_name=template_name,
                                            extra_context=extra_context)

    @property
    def template(self):
        template_name = TPL_PATH + '_waitingforconfirm.html'
        return template_name
