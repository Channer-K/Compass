# -*- coding: utf-8 -*-
from compass import models
from django import forms
from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext as _


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'value': '@pset.suntec.net'}))

    class Meta:
        model = models.User

    def clean_username(self):
        username = self.cleaned_data.get('username').lower()
        return username

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
            'fields': ('is_active', 'is_staff', 'groups', 'roles',
                       'user_permissions')
            }),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'password1', 'password2')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'groups', 'roles',)}),
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

    def get_queryset(self, request):
        qs = super(MyUserAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            return qs.filter(pk__in=[
                u.pk for u in request.user.get_subordinate_users()])

    def save_model(self, request, obj, form, change):
        obj.save()

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups' and not request.user.is_superuser:
            kwargs['queryset'] = models.Group.objects.filter(pk__in=[
                g.pk for g in request.user.get_subordinate_groups()])
        elif db_field.name == 'roles' and not request.user.is_superuser:
            kwargs['queryset'] = models.Role.objects.filter(group__in=list(
                request.user.get_subordinate_groups()))

        return super(MyUserAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    # Override relative response_add function in UserAdmin class.
    def response_add(self, request, obj, post_url_continue=None):
        return super(UserAdmin, self).response_add(
            request, obj, post_url_continue=None)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif not obj and request.user.is_leader:
            return True
        elif obj in request.user.get_subordinate_users():
            return True

        return False

    has_delete_permission = has_change_permission
    has_add_permission = has_change_permission


class MyGroupAdmin(MPTTModelAdmin):
    fields = ('name', 'parent', 'permissions',)
    filter_horizontal = ('permissions',)


class RoleForm(forms.ModelForm):

    class Meta:
        model = models.Role
        fields = ('name', 'group', 'superior', 'is_leader', 'permissions',)


class RoleAdmin(admin.ModelAdmin):
    form = RoleForm

    list_filter = ('group',)
    filter_horizontal = ('permissions',)
    list_display = ('name', 'group', 'superior', 'is_leader')

    def get_form(self, request, obj=None, **kwargs):
        form = super(RoleAdmin, self).get_form(request, obj=None, **kwargs)
        if obj:
            form.base_fields['is_leader'].initial = obj.is_leader

        return form


class ModuleAdmin(admin.ModelAdmin):
    list_filter = ('group',)
    list_display = ('name', 'group')

    def get_queryset(self, request):
        qs = super(ModuleAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            return qs.filter(group__in=[
                g for g in request.user.get_subordinate_groups()])

    def save_model(self, request, obj, form, change):
        obj.save()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'group' and not request.user.is_superuser:
            kwargs['queryset'] = models.Group.objects.filter(pk__in=[
                g.pk for g in request.user.get_subordinate_groups()])

        return super(ModuleAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif not obj and request.user.is_leader:
            return True
        elif obj.group in request.user.get_subordinate_groups():
            return True

        return False

    has_delete_permission = has_change_permission
    has_add_permission = has_change_permission


class ServerAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'ip', 'is_active', 'comment')
    filter_horizontal = ('groups',)


class ServerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'environment', 'comment')


admin.site.unregister(models.Group)
admin.site.register(models.User, MyUserAdmin)
admin.site.register(models.Group, MyGroupAdmin)
admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Environment)
admin.site.register(models.ServerGroup, ServerGroupAdmin)
admin.site.register(models.Module, ModuleAdmin)
admin.site.register(models.Role, RoleAdmin)
