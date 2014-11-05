# -*- coding: utf-8 -*-
import os
from compass.conf import settings
from django.conf import settings as djsettings
from django.utils.safestring import mark_safe
from django.http import HttpResponseForbidden
from django.views.generic import TemplateView


_ERROR_MSG = '''
    <!DOCTYPE html>
    <html lang="zh">
        <body>
            <h1>%s</h1>
            <p>%%s</p>
        </body>
    </html>
'''

_400_ERROR = _ERROR_MSG % '400 Bad Request'
_403_ERROR = _ERROR_MSG % '403 Forbidden'
_405_ERROR = _ERROR_MSG % '405 Not Allowed'


class StaticUrls(object):
    """
    This class allow to automatically find any template file that ends
    with .html and set up for each one an url address for
    direct redirection.

    Eg.
    /about/ will redirect to /project/path/templates/about.html
    /contact/email/ will redirect to /project/path/templates/contact/
    email.html
    """

    def listfiles(self, dir, path):
        """
        This recursive method search file that ends with .html
        in a directory tree
        """

        files = []
        for res in os.listdir(dir):

            # Directory
            if os.path.isdir(os.path.join(dir, res)):
                # If element is a directory i do a recursive call
                files += self.listfiles(
                    dir=os.path.join(dir, res),
                    path=os.path.join(path, res)
                )
            # Files
            else:
                # If element is a file, i check filename end and,
                # if positive,
                # i add path and url to a list
                if res.endswith(".html"):
                    files.append({
                        "url": os.path.join(path, res),
                        "file": os.path.join(path, res),
                    })

        return files

    def discover(self):
        """
        This method will scan any template dir and add url for each valid
        static file
        """
        template_dirs = djsettings.TEMPLATE_DIRS
        patterns = []
        for td in template_dirs:
            urls = self.listfiles(td, "")
            for url in urls:
                # i will create a list with the same struct of django url
                # pattern.
                # direct_to_template is a django view function for
                # redirection to files
                patterns.append((
                    r'^history/%s$' % url['url'],
                    TemplateView.as_view(template_name=url['file']),
                ))
        return patterns


def httpForbidden(err_code=403, err_content=''):
    if err_code == 400:
        error_message = _400_ERROR % err_content
    elif err_code == 403:
        error_message = _403_ERROR % err_content
    elif err_code == 405:
        error_message = _405_ERROR % err_content

    return HttpResponseForbidden(mark_safe(error_message))


def generate_url_token():
    import uuid
    return uuid.uuid4().hex


def save_snapshot(token, content):
    save_path = djsettings.TEMPLATE_DIRS
    for path in save_path:
        complete_filename = os.path.join(path, token + '.html')
        fh = open(complete_filename, 'w')
        fh.write(content.encode('utf8'))
        fh.close()
    return


def get_right_assignee(exclude=[]):
    from compass.models import Group

    SA_GROUP = Group.objects.get(pk=settings.SA_GID)
    groups = SA_GROUP.get_descendants(include_self=True)

    users = set()
    for group in groups:
        for user in group.user_set.all():
            if (not user.at_work and user.is_leader
                    or (exclude and user in exclude)):
                continue
            users.add(user)

    users_list = list(users)

    mrRight = users_list[0]
    if len(users_list) > 1:
        for user in users_list[1:]:
            num = user.get_count_inprogress()
            if num and num <= mrRight.get_count_inprogress():
                mrRight = user

    return mrRight


def get_all_online_SAs():
    from compass.models import Group
    online_SAs = set()

    SA = Group.objects.get(pk=settings.SA_GID)
    for group in SA.get_descendants(include_self=True):
        online_SAs.update(group.user_set.all().filter(at_work=True))

    return online_SAs
