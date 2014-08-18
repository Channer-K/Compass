# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext as _
from compass import models


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'placeholder': '@pset.suntec.net'}))

    class Meta:
        model = models.User
        fields = ('email',)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean_email(self):
        email = self.cleaned_data['email']
        if "@pset.suntec.net" not in email:
            raise forms.ValidationError(
                "Email Address must end with @pset.suntec.net")
        return email

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = models.User

    def clean_password(self):
        return self.initial["password"]


class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'groups', 'roles', 'user_permissions')
            }),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'password1', 'password2', 'email')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'in_groups', 'is_staff')
    list_filter = ('is_active', 'groups')

    readonly_fields = ('created_at', 'last_login',)
    filter_horizontal = ('groups', 'roles', 'user_permissions',)

    form = UserChangeForm
    add_form = UserCreationForm

    def in_groups(self, obj):
        return ", ".join([p.name for p in obj.groups.all()])


class MyGroupAdmin(MPTTModelAdmin):
    fields = ('name', 'parent', 'permissions', 'modules',)
    filter_horizontal = ('permissions', 'modules',)


class RoleAdmin(admin.ModelAdmin):
    fields = ('name', 'group',)
    list_display = ('name', 'group',)


class ServerAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'ip', 'is_active', 'comment')
    filter_horizontal = ('groups',)


class ServerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'environment', 'comment')


class PackageInline(admin.TabularInline):
    fk_name = 'task'
    fields = ('filename', 'path', 'authors', 'comment',)
    exclude = ('created_at', 'is_published',)
    model = models.Package
    extra = 1


class TaskForm(forms.ModelForm):
    environment = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=models.Environment.objects.all())

    class Meta:
        model = models.Task


class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ('modules_list', 'version', 'created_at',)
    filter_horizontal = ('modules',)
    inlines = [PackageInline]

    def get_form(self, request, obj=None, **kwargs):
        # Proper kwargs are form, fields, exclude, formfield_callback
        if obj:
            self.readonly_fields = ['applicant', 'created_at']
        else:
            kwargs['exclude'] = ['accept_group', 'applicant', 'created_at']
        return super(TaskAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.applicant = request.user
            obj.save()
            for env in request.POST.getlist('environment'):
                env_obj = models.Environment.objects.get(pk=env)
                models.Subtask.objects.create(task=obj, environment=env_obj)

    def modules_list(self, obj):
        return ", ".join([p.name for p in obj.modules.all()])


admin.site.unregister(Group)
admin.site.register(models.User, MyUserAdmin)
admin.site.register(Group, MyGroupAdmin)
admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Environment)
admin.site.register(models.ServerGroup, ServerGroupAdmin)
admin.site.register(models.Module)
admin.site.register(models.Role, RoleAdmin)
admin.site.register(models.Task, TaskAdmin)
