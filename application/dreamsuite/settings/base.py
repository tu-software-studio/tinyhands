from django.contrib import messages
from unipath import Path
import os
import sys
import logging.config
import datetime
from azure.identity import DefaultAzureCredential

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

SITE_DOMAIN = os.environ['SITE_DOMAIN']
CLIENT_DOMAIN = os.environ['CLIENT_DOMAIN']
FCM_KEY_PATH = os.environ['FCM_KEY_PATH']

BASE_DIR = Path(__file__).ancestor(3)

SERVER_EMAIL = 'support@searchlightdata.org'

EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_PORT = os.environ['EMAIL_PORT']
EMAIL_USE_TLS = os.environ['EMAIL_USE_TLS']
EMAIL_HOST = os.environ['EMAIL_HOST']

BORDER_STATION_EMAIL_SENDER = "sheital@tinyhands.org"
ADMIN_EMAIL_SENDER = SERVER_EMAIL
DEFAULT_FROM_EMAIL = SERVER_EMAIL

ALERT_INTERVAL_IN_DAYS = 30

DEBUG = False

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

FIXTURE_DIRS = (
    os.path.join(BASE_DIR, 'fixtures'),
)

AUTH_USER_MODEL = 'accounts.Account'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_URL = '/logout/'
EXPIRING_TOKEN_LIFESPAN = datetime.timedelta(hours=10)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'widget_tweaks',
    'bootstrapform',
    'imagekit',
    'dataentry',
    'firebase',
    'accounts',
    'legal',
    'events',
    'portal',
    'budget',
    'id_matching',
    'face_matching',
    'util',
    'static_border_stations',
    'rest_api',
    'rest_framework',
    'django_extensions',
    'rest_framework.authtoken',
    'django_filters',
    'help',
    'rest_framework_jwt',  # Security tokens for auth0
    'azure_storage',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',  # Auth0
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'dreamsuite.urls'

WSGI_APPLICATION = 'dreamsuite.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': os.environ['DB_HOST'],
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASS'],
        'PORT': os.environ['DB_PORT'],
    }
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kathmandu'

USE_I18N = False
USE_L10N = False
USE_TZ = True

DATETIME_FORMAT = "n.j.Y g:iA"
DATE_FORMAT = "n.j.Y"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)
STATIC_ROOT = os.path.normpath(os.path.join(SITE_ROOT, "../static"))
STATIC_URL = '/static/'

# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/cloud-media/'

PUBLIC_ROOT = os.path.join(BASE_DIR, 'public')
PUBLIC_URL = '/public/'

STORAGES = {
    "default": {
        # "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "BACKEND": "azure_storage.azure_storage_with_reverse_proxy.AzureStorageWithReverseProxy",
        "OPTIONS": {
            # Try a bunch of different Azure login methods until one works
            "token_credential": DefaultAzureCredential(),
            # Ideally we would use Managed Identities instead
            # https://mijailovic.net/2019/11/01/django-managed-identitites/
            # Or we would use a Key Vault
            # But it looks like it is quite a process to set up and I don't really understand it
            "account_name": os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
            "account_key": os.environ.get("AZURE_ACCOUNT_KEY"),
            # Create this in the Storage Browser of your Azure Storage Account before use
            "azure_container": os.environ.get("AZURE_CONTAINER"),
            # Currently the IRF saves files twice in a row, or something
            # Because overwriting is the default with the normal FileStorage
            # Set this to preserve current functionality
            "overwrite_files": True,
        },
    },
    "staticfiles": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "filesystem": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "mediabackups": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            # Try a bunch of different Azure login methods until one works
            "token_credential": DefaultAzureCredential(),
            # Ideally we would use Managed Identities instead
            # https://mijailovic.net/2019/11/01/django-managed-identitites/
            # Or we would use a Key Vault
            # But it looks like it is quite a process to set up and I don't really understand it
            "account_name": os.environ.get("AZURE_BACKUP_STORAGE_ACCOUNT_NAME"),
            "account_key": os.environ.get("AZURE_BACKUP_ACCOUNT_KEY"),
            # Create this in the Storage Browser of your Azure Storage Account before use
            "azure_container": os.environ.get("AZURE_BACKUP_CONTAINER"),
        },
    },
}

TEST_ENVIRONMENT = len(sys.argv) > 1 and sys.argv[1] == 'test'

MESSAGE_TAGS = {
    messages.constants.ERROR: 'danger'  # Fix up for Bootstrap.
}

SERIALIZATION_MODULES = {
        "form_data_id": "export_import.form_data_id_serializer",
        "form_data_tag": "export_import.form_data_tag_serializer",
    }

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "templates")
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                "django.template.context_processors.request",
                'django.contrib.messages.context_processors.messages',
                "dataentry.context_processors.border_stations_processor",
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',  # Auth0
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'accounts.expiring_token_authentication.ExpiringTokenAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_api.pagination.DefaultPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default
    'django.contrib.auth.backends.RemoteUserBackend',  # Auth0
]
# Auth0
JWT_AUTH = {
    'JWT_PAYLOAD_GET_USERNAME_HANDLER':
        'util.auth0.jwt_get_username_from_payload_handler',
    'JWT_DECODE_HANDLER':
        'util.auth0.jwt_decode_token',
    'JWT_ALGORITHM': 'RS256',
    'JWT_AUDIENCE': os.environ.get('AUTH0_AUDIENCE_ID', 'UNSET_AUTH0_AUDIENCE_ID'),
    'JWT_ISSUER': os.environ.get('AUTH0_DOMAIN', 'UNSET_AUTH0_DOMAIN'),
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format':
                '%(levelname)s|%(asctime)s|%(name)s[%(lineno)s-%(funcName)s]>> %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.environ['DREAMSUITE_LOG'],
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'export_import': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'export_import.google_sheet_work_queue': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dataentry': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'budget.views': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'googleapiclient': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'recordlinkage': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        }
    },
}

logging.config.dictConfig(LOGGING)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
