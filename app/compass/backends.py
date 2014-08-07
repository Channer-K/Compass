from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission


class MyModelBackend(object):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)

    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_group_perm_cache'):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                user_groups_field = get_user_model()._meta.get_field('groups')
                user_groups_query = 'group__%s' % user_groups_field.related_query_name()
                perms = Permission.objects.filter(**{user_groups_query: user_obj})
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            user_obj._group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._group_perm_cache

    def get_role_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        roles.
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_role_perm_cache'):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                user_roles_field = get_user_model()._meta.get_field('roles')
                user_roles_query = 'role__%s' % user_roles_field.related_query_name()
                perms = Permission.objects.filter(**{user_roles_query: user_obj})
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            user_obj._role_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._role_perm_cache

    def get_all_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = set(["%s.%s" % (p.content_type.app_label, p.codename) for p in user_obj.user_permissions.select_related()])
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
            user_obj._perm_cache.update(self.get_role_permissions(user_obj))
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        if not user_obj.is_active:
            return False
        for perm in self.get_all_permissions(user_obj):
            if perm[:perm.index('.')] == app_label:
                return True
        return False

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
