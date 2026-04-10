from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

SECRET_KEY = 'dev-insecure-key-never-use-in-prod'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'helpdesk_dev',
        'USER': 'helpdesk',
        'PASSWORD': 'helpdesk',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Sobreescribir con SQLite para correr sin Docker si se necesita
import os
if os.getenv('USE_SQLITE'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
