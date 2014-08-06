from __future__ import unicode_literals
from django.contrib.auth import get_user_model


class ModelBackend(object):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, username=None, password=None, **kwargs):
        pass

    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        pass

    def get_role_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        roles.
        """
        pass

    def get_all_permissions(self, user_obj, obj=None):
        pass

    def has_perm(self, user_obj, perm, obj=None):
        pass

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        pass

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
