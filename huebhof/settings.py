"""
Django settings for huebhof project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('JUNTAGRICO_SECRET_KEY')

DEBUG = os.environ.get("JUNTAGRICO_DEBUG", 'False')=='True'

ALLOWED_HOSTS = ['huebhof.juntagrico.science', 'localhost', 'my.huebhof.org' ]

# Admin Settings
ADMINS = [
    ('Admin', os.environ.get('JUNTAGRICO_ADMIN_EMAIL'))
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'huebhof',
    'juntagrico_billing',
    'juntagrico',
    'fontawesomefree',
    'import_export',
    'impersonate',
    'crispy_forms',
    'adminsortable2',
    'polymorphic',
    
]

ROOT_URLCONF = 'huebhof.urls'
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('JUNTAGRICO_DATABASE_ENGINE','django.db.backends.sqlite3'), 
        'NAME': os.environ.get('JUNTAGRICO_DATABASE_NAME','huebhof.db'), 
        'USER': os.environ.get('JUNTAGRICO_DATABASE_USER'), #''junatagrico', # The following settings are not used with sqlite3:
        'PASSWORD': os.environ.get('JUNTAGRICO_DATABASE_PASSWORD'), #''junatagrico',
        'HOST': os.environ.get('JUNTAGRICO_DATABASE_HOST'), #'localhost', # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': os.environ.get('JUNTAGRICO_DATABASE_PORT', False), #''', # Set to empty string for default.
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'huebhof/templates')],  # location of your overriding templates
        'APP_DIRS': True,  # Option 1: This is needed for addons that override templates
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader'
            ],
            'debug' : True
        },
    },
]

WSGI_APPLICATION = 'huebhof.wsgi.application'


LANGUAGE_CODE = 'de'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

DATE_INPUT_FORMATS =['%d.%m.%Y',]

AUTHENTICATION_BACKENDS = (
    'juntagrico.util.auth.AuthenticateWithEmail',
    'django.contrib.auth.backends.ModelBackend'
)


MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware'
    
]

EMAIL_HOST = os.environ.get('JUNTAGRICO_EMAIL_HOST')
EMAIL_HOST_USER = os.environ.get('JUNTAGRICO_EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('JUNTAGRICO_EMAIL_PASSWORD')
EMAIL_PORT = int(os.environ.get('JUNTAGRICO_EMAIL_PORT', '25'))
EMAIL_USE_TLS = os.environ.get('JUNTAGRICO_EMAIL_TLS', 'False')=='True'
EMAIL_USE_SSL = os.environ.get('JUNTAGRICO_EMAIL_SSL', 'False')=='True'

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

WHITELIST_EMAILS = ['admin@huebhof.org']

def whitelist_email_from_env(var_env_name):
    email = os.environ.get(var_env_name)
    if email:
        WHITELIST_EMAILS.append(email.replace('@gmail.com', '(\+\S+)?@gmail.com'))


if DEBUG is True:
    for key in os.environ.keys():
        if key.startswith("JUNTAGRICO_EMAIL_WHITELISTED"):
            whitelist_email_from_env(key)
            


STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}
LOCALE_PATHS = ('locale',)

IMPERSONATE = {
    'REDIRECT_URL': '/my/profile',
}

LOGIN_REDIRECT_URL = "/"

"""
    File & Storage Settings
"""
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

MEDIA_ROOT = 'media'

"""
     Crispy Settings
"""
CRISPY_TEMPLATE_PACK = 'bootstrap4'

"""
JUNTAGRICO SETTINGS
"""

IMPORT_EXPORT_EXPORT_PERMISSION_CODE = 'view'

"""
Contact Information
"""
ORGANISATION_NAME = "HUEBHOF"
ORGANISATION_LONG_NAME = "SOLAWI HUEBHOF"
ORGANISATION_ADDRESS = {"name":"Huebhof GmbH", 
            "street" : "Probsteistrasse",
            "number" : "26",
            "zip" : "8051",
            "city" : "Zürich",
            "extra" : ""}
# ORGANISATION_PHONE = ""
CONTACTS = {
"general" : "solawi@huebhof.org"
}
ORGANISATION_WEBSITE = {
    'name' : "www.huebhof.org",
    'url': "https://www.huebhof.org"
}

"""
Accounting
"""
ORGANISATION_BANK_CONNECTION = {"PC" : "-",
            "IBAN" : "CH90 3012 3039 0058 1010 5",
            "BIC" : "ABSOCH22",
            "NAME" : "Alternative Bank Schweiz AG",
            "ESR" : ""}
DEFAULT_FROM_EMAIL = "admin@huebhof.org"
BILLS_USERMENU = True

"""
External Documents
"""
# BUSINESS_REGULATIONS = "https://huebhof.org/wp-content/uploads/2022/11/Huebhof2023_News_1.pdf" # URL to your business regulations document
# BYLAWS = "https://huebhof.org/wp-content/uploads/2022/11/Huebhof2023_News_1.pdf" # URL to your bylaws document
# FAQ_DOC = "https://huebhof.org/wp-content/uploads/2022/11/Huebhof2023_News_1.pdf" # URL to your FAQ document
EXTRA_SUB_INFO = "https://huebhof.org/wp-content/uploads/2023/12/Vereinbarung_Ernteanteil_Gemuese_Obst_Eier.pdf" # If you use extra subscriptions this describes the URL to the document describing them
# ACTIVITY_AREA_INFO = "" # URL to your document describing your activity areas

"""
Business Year / Membership
"""
BUSINESS_YEAR_START = {"day": 1, "month": 1} # Defining the start of the business year
BUSINESS_YEAR_CANCELATION_MONTH = 9 # The date until you can cancel your subscriptions
MEMBERSHIP_END_MONTH = 12
MEMBERSHIP_END_NOTICE_PERIOD = 3

"""
Shares
"""
ENABLE_SHARES = False #Enable all share related funtionality
SHARE_PRICE = "250"

"""
Jobs
"""
ASSIGNMENT_UNIT = "HOURS"

"""
Appearance
"""
VOCABULARY = {
    'member': 'Mitglied',
    'member_pl' : 'Mitglieder',
    'assignment' : 'Arbeitseinsatz',
    'assignment_pl' : 'Arbeitseinsätze',
    'share' : 'Anteilschein',
    'share_pl' : 'Anteilscheine',
    'subscription' : 'Ernteanteil',
    'subscription_pl' : 'Ernteanteile',
    'co_member' : 'Mitabonnent:in',
    'co_member_pl' : 'Mitabonnenten:innen',
    'price' : 'Betriebsbeitrag',
    'member_type' : 'Mitglied',
    'member_type_pl' : 'Mitglieder',
    'depot' : 'Depot',
    'depot_pl' : 'Depots',
    'package': 'Tasche',
}
STYLES = {'static': ['/huebhof/css/customize.css']}
FAVICON = "/static/huebhof/img/huebhof_33x33.ico"
IMAGES = {'status_100': '/static/huebhof/img/karotte_voll.png',
    'status_75': '/static/juntagrico/img/status_75.png',
    'status_50': '/static/juntagrico/img/status_50.png',
    'status_25': '/static/juntagrico/img/status_25.png',
    'status_0': '/static/huebhof/img/karotte_leer.png',
    'single_full': '/static/huebhof/img/karotte_voll.png',
    'single_empty': '/static/huebhof/img/karotte_leer.png',
    'single_core': '/static/huebhof/img/kern.png',
    'core': '/static/juntagrico/img/core.png'}

TIME_ZONE = 'Europe/Zurich'
USE_TZ = True

"""
EMAIL
"""

MAIL_TEMPLATE = "mails/email.html"

FROM_FILTER = {
    'filter_expression': 'admin@huebhof\.org',
    'replacement_from': 'admin@huebhof.org'
}

DEFAULT_MAILER = 'juntagrico.util.mailer.batch.Mailer'
BATCH_MAILER = {
    'batch_size': 39,
    'wait_time': 65
}