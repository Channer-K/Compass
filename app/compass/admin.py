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
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'password1', 'password2', 'email')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'in_groups', 'is_staff')
    list_filter = ('is_active', 'groups')

    readonly_fields = ('date_joined', 'last_login',)
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
    list_display = ('name', 'place', 'comment')

admin.site.unregister(Group)
admin.site.register(models.User, MyUserAdmin)
admin.site.register(Group, MyGroupAdmin)
admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Place)
admin.site.register(models.ServerGroup, ServerGroupAdmin)
admin.site.register(models.Module)
admin.site.register(models.Role, RoleAdmin)
