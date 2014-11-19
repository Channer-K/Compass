# -*- coding: utf-8 -*-
from django import forms
from compass.models import *
from compass.conf import settings
from django.utils.text import capfirst
from compass.utils.permissions import modules_can_access
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext_lazy as _


class SigninForm(forms.Form):

    """
    Base class for authenticating users.
    Extend this to get a form that accepts username/password logins.
    """
    username = forms.CharField(max_length=30, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    error_messages = {
        'invalid_login': _("Please enter a correct %(username)s and password."
                           " Note that both fields may be case-sensitive."),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super(SigninForm, self).__init__(*args, **kwargs)

        # Set the label for the "username" field.
        UserModel = get_user_model()
        self.username_field = UserModel._meta.get_field(
            UserModel.USERNAME_FIELD)
        if self.fields['username'].label is None:
            self.fields['username'].label = capfirst(
                self.username_field.verbose_name)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username,
                                           password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(self.error_messages['inactive'],
                                            code='inactive',)
        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class MultiFileInput(forms.FileInput):

    def render(self, name, value, attrs={}):
        attrs['multiple'] = 'multiple'
        return super(MultiFileInput, self).render(name, None, attrs=attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            return [files.get(name)]


class MultiFileField(forms.FileField):
    widget = MultiFileInput
    default_error_messages = {
        'min_num': u"Ensure at least %(min_num)s files are uploaded (received %(num_files)s).",
        'max_num': u"Ensure at most %(max_num)s files are uploaded (received %(num_files)s).",
        'file_size': u"File: %(uploaded_file_name)s, exceeded maximum upload size limit %(limit_size)s M.",
        'error_ext': u'File type is not supported.'
    }

    def __init__(self, *args, **kwargs):
        self.min_num = kwargs.pop('min_num', 0)
        self.max_num = kwargs.pop('max_num', None)
        self.maximum_file_size = kwargs.pop('maximum_file_size', None)
        super(MultiFileField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        ret = []
        for item in data:
            ret.append(super(MultiFileField, self).to_python(item))
        return ret

    def validate(self, data):
        super(MultiFileField, self).validate(data)
        num_files = len(data)
        if len(data) and not data[0]:
            num_files = 0
            return
        if num_files < self.min_num:
            raise forms.ValidationError(
                self.error_messages['min_num'] % {'min_num': self.min_num,
                                                  'num_files': num_files})
        elif self.max_num and num_files > self.max_num:
            raise forms.ValidationError(
                self.error_messages['max_num'] % {'max_num': self.max_num,
                                                  'num_files': num_files})

        for uploaded_file in data:
            if uploaded_file.size > self.maximum_file_size:
                raise forms.ValidationError(
                    self.error_messages['file_size'] %
                    {'uploaded_file_name': uploaded_file.name,
                     'limit_size': settings.MAX_UPLOAD_SIZE / 1024 / 1024})

            content_type = uploaded_file.content_type
            if content_type not in settings.CONTENT_TYPES:
                raise forms.ValidationError(self.error_messages['error_ext'])

        return


class ReplyForm(forms.Form):
    subject = forms.CharField(
        label=u'标题', max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    content = forms.CharField(
        label=u'内容',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))
    uploaded_file = MultiFileField(max_num=10, min_num=0,
                                   maximum_file_size=settings.MAX_UPLOAD_SIZE)


class ProfileForm(forms.Form):
    error_messages = {
        'password_incorrect': _("Your old password was entered incorrectly. "
                                "Please enter it again."),
        'password_mismatch': _("The two password fields didn't match."),
        'password_same': _("Your old and new password are the same."
                           "Please enter your passwords again."),
        'password_required': _("New password is required."),
    }
    first_name = forms.CharField(
        required=False, label=u'First name', max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=False, label=u'Last name', max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label=u"Email", max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control',
                                       'placeholder': '@pset.suntec.net'})
    )

    old_password = forms.CharField(
        required=False, label=_("Old password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        required=False, label=_("New password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        required=False, label=_("New password confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if old_password and not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

    def clean_new_password1(self):
        old_password = self.cleaned_data.get("old_password")
        password1 = self.cleaned_data.get('new_password1')
        if old_password and not password1:
            raise forms.ValidationError(
                self.error_messages['password_required'],
                code='password_required',
            )
        if old_password and old_password == password1:
            raise forms.ValidationError(
                self.error_messages['password_same'],
                code='password_same',
            )
        return password1

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def clean_email(self):
        email = self.cleaned_data['email']
        if "@pset.suntec.net" not in email:
            raise forms.ValidationError(
                "Email address must end with @pset.suntec.net")
        return email

    def save(self, commit=True):
        update_fields = []
        if self.cleaned_data["old_password"]:
            self.user.set_password(self.cleaned_data["new_password1"])
            update_fields.append('password')
        if commit:
            if self.user.first_name != self.cleaned_data["first_name"]:
                self.user.first_name = self.cleaned_data["first_name"]
                update_fields.append('first_name')
            if self.user.last_name != self.cleaned_data["last_name"]:
                self.user.last_name = self.cleaned_data["last_name"]
                update_fields.append('last_name')
            if self.user.email != self.cleaned_data["email"]:
                self.user.email = self.cleaned_data["email"]
                update_fields.append('email')

            self.user.save(update_fields=update_fields)
        return self.user


class FilterForm(forms.Form):
    from_date = forms.DateField(label=u'开始时间', input_formats=['%Y-%m-%d'])
    to_date = forms.DateField(label=u'结束时间', input_formats=['%Y-%m-%d'])

    def __init__(self, request, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)
        self.request = request
        self.user_cache = request.user

        if self.user_cache is None:
            return

        self.fields['modules'] = forms.MultipleChoiceField(
            label=u'发布模块',
            widget=forms.SelectMultiple(attrs={
                'class': 'chosen-select',
                'style': 'width: 300px',
                'data-placeholder': 'Choose release modules...'}),
            choices=[(module.pk, module.name) for module
                     in modules_can_access(self.user_cache)])


class NewTaskForm(forms.ModelForm):
    environment = forms.ModelMultipleChoiceField(
        label=u'发布环境',
        queryset=Environment.objects.all(),
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Task
        fields = ['version', 'ticket_num', 'modules', 'amendment',
                  'explanation', 'comment']
        widgets = {
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'ticket_num': forms.TextInput(attrs={'class': 'form-control'}),
            'amendment': forms.TextInput(attrs={'class': 'form-control'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control',
                                                 'rows': '5'}),
            'comment': forms.Textarea(attrs={'class': 'form-control',
                                             'rows': '3'}),
        }
        error_messages = {
            'version': {'max_length': "Version is too long.", },
            'ticket_num': {'max_length': "Ticket Number is too long.", },
            'amendment': {'max_length': "Amendment is too long.", },
            'explanation': {'max_length': "Explanation is too long.", },
        }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = request.user
        super(NewTaskForm, self).__init__(*args, **kwargs)

        self.fields['modules'] = forms.MultipleChoiceField(
            label=u'发布模块',
            widget=forms.SelectMultiple(attrs={
                'class': 'chosen-select',
                'style': 'width: 482px',
                'data-placeholder': 'Choose release modules...'}),
            choices=[(module.pk, module.name) for module
                     in modules_can_access(self.user_cache)])

    def save(self, commit=True, force_insert=False, eids=None,
             force_update=False, *args, **kwargs):
        task = super(NewTaskForm, self).save(commit=False, *args, **kwargs)
        task.applicant = self.user_cache

        task.save()
        self.save_m2m()

        """
        Create the subtasks using by environment and update progressing_id
        in task to the pk of the first subtask.
        """
        env = Environment.objects.get(pk=eids[0])
        progressing = task.subtask_set.create(environment=env)
        task.progressing_id = progressing.pk
        task.save(update_fields=['progressing_id'])

        for eid in eids[1:]:
            env = Environment.objects.get(pk=eid)
            task.subtask_set.create(environment=env)

        auditors = list(self._get_auditors(task))
        if auditors:
            task.auditor = auditors[0]
            task.save(update_fields=['auditor'])
        else:
            task.available = True
            task.auditor = self.user_cache
            task.save(update_fields=['auditor', 'available'])

            task.make_available()

        return task

    def _get_auditors(self, task):
        auditors = set()

        for module in task.modules.all():
            superior = self.user_cache.role_in_group(module.group).superior
            if superior:
                auditors.update(superior.user_set.all())

        return auditors


class PackageForm(forms.ModelForm):

    class Meta:
        model = Package
        fields = ('filename', 'path', 'authors', 'comment',)
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'path': forms.TextInput(attrs={'class': 'form-control'}),
            'authors': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control',
                                             'rows': '3'}),
        }
