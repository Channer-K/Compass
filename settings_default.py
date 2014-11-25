"""
Django settings for app project.

"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.conf import *
PROJECT_DIR = os.path.join(BASE_DIR, 'compass')


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['*']
DEFAULT_FROM_EMAIL = 'no-reply@compass.sys'


# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'compass',
    'mptt',
    'pipeline',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'compass.utils.middleware.AutoLogout',
)

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request',
)

ROOT_URLCONF = 'app.urls'
AUTH_USER_MODEL = 'compass.User'
WSGI_APPLICATION = 'app.wsgi.application'
AUTHENTICATION_BACKENDS = ('compass.backends.MyModelBackend',)


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'compass',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
    )

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
PIPELINE_YUGLIFY_BINARY = os.path.join(BASE_DIR,
                                       'node_modules/yuglify/bin/yuglify')

PIPELINE_CSS = {
    'master': {
        'source_filenames': ('css/reset.css',
                             'css/bootstrap.css',
                             'css/flat-ui.css',
                             'css/chosen.css',
                             'css/style.css'),
        'output_filename': 'css/master.css',
    },
    'jquery': {
        'source_filenames': ('css/jquery-ui*.css',
                             'css/jquery-ui-timepicker-addon.css',
                             ),
        'output_filename': 'css/jquery.css',
    }
}

PIPELINE_JS = {
    'master': {
        'source_filenames': ('js/jquery.js',
                             'js/bootstrap*.js',
                             'js/jquery-ui.js',
                             'js/jquery-ui-*.js',
                             'js/chosen.jquery.min.js',
                             'js/flatui*.js',),
        'output_filename': 'js/master.js',
    },
    'vendor': {
        'source_filenames': ('js/sb-admin-2.js',
                             'js/metisMenu.js',),
        'output_filename': 'js/vendor.js',
    },
    'custom': {
        'source_filenames': ('js/application.js',
                             'js/compass.js',),
        'output_filename': 'js/custom.js',
    }
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

TEMPLATE_DIRS = [os.path.join(PROJECT_DIR, 'snapshots')]
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'upload')
MEDIA_URL = '/upload/'
LOGIN_URL = '/signin/'
LOGIN_REDIRECT_URL = '/'

# Email
EMAIL_HOST = 'localhost'

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
# Auto logout delay in minutes
AUTO_LOGOUT_DELAY = 20

BROKER_URL = 'amqp://guest:guest@localhost//'
CELERY_TIMEZONE = 'Asia/Shanghai'

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'notify-in-office-day': {
        'task': 'compass.tasks.task_notification',
        'schedule': crontab(minute='0', hour='9-18/3', day_of_week='mon-fri'),
    },
    'change-in-office-day': {
        'task': 'compass.tasks.change_status',
        'schedule': crontab(minute='30', hour='9-18/1', day_of_week='mon-fri'),
    },
}
