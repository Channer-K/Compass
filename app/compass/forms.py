# -*- coding: utf-8 -*-
import warnings
from compass.models import *
from django import forms
from django.utils.text import capfirst
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext_lazy as _


class SigninForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
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
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return self.cleaned_data

    def check_for_test_cookie(self):
        warnings.warn("check_for_test_cookie is deprecated; ensure your login"
                      "view is CSRF-protected.", DeprecationWarning)

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    uploaded_file = forms.FileField()


class FilterForm(forms.Form):
    from_date = forms.DateField(label=u'开始时间', input_formats=['%Y-%m-%d'])
    to_date = forms.DateField(label=u'结束时间', input_formats=['%Y-%m-%d'])
    modules = forms.MultipleChoiceField(label=u'发布模块', choices=[],
                                        widget=forms.CheckboxSelectMultiple())
    status = forms.MultipleChoiceField(
        label=u'任务状态',
        choices=[(1, u'等待审核'), (2, u'等待发布'), (3, u'发布中')],
        widget=forms.CheckboxSelectMultiple())

    def __init__(self, user=None, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)

        if user is not None:
            UserModel = get_user_model()
            self.user = UserModel._default_manager.get(username=user)
            self.fields['modules'].choices = self.user.all_modules_choices()


class ProfileForm(forms.Form):
    error_messages = {
        'password_incorrect': _("Your old password was entered incorrectly. "
                                "Please enter it again."),
        'password_mismatch': _("The two password fields didn't match."),
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
        widget=forms.EmailInput(attrs={'class': 'form-control'}))

    old_password = forms.CharField(
        required=False, label=_("Old password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(
        required=False, label=_("New password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(
        required=False, label=_("New password confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password) and old_password:
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

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


class NewTaskForm(forms.ModelForm):
    environment = forms.ModelMultipleChoiceField(
        label=u'发布环境',
        queryset=Environment.objects.all(),
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Task
        fields = ['version', 'modules', 'amendment', 'explanation', 'comment']
        widgets = {
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'amendment': forms.TextInput(attrs={'class': 'form-control'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control',
                                                 'rows': '5'}),
            'comment': forms.Textarea(attrs={'class': 'form-control',
                                             'rows': '3'}),
        }
        error_messages = {
            'version': {'max_length': "Version is too long.", },
            'amendment': {'max_length': "Amendment is too long.", },
            'explanation': {'max_length': "Explanation is too long.", },
        }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = request.user
        super(NewTaskForm, self).__init__(*args, **kwargs)

        self.fields['modules'] = forms.MultipleChoiceField(
            label=u'发布模块', widget=forms.CheckboxSelectMultiple(),
            choices=self.user_cache.all_modules_choices())

    def save(self, commit=True, force_insert=False, eids=None,
             force_update=False, *args, **kwargs):
        task = super(NewTaskForm, self).save(commit=False, *args, **kwargs)
        task.applicant = self.user_cache
        task.save()
        self.save_m2m()

        if eids is not None:
            # Active the first subtask
            env = Environment.objects.get(pk=eids[0])
            st = Subtask.objects.create(task=task, environment=env)
            task.progressing_id = st.pk
            task.save(update_fields=['progressing_id'])

            for eid in eids[1:]:
                env = Environment.objects.get(pk=eid)
                Subtask.objects.create(task=task, environment=env)

        return task


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
