"""
Configuración de Django para el servicio de Help Desk.

Un único archivo de settings; no hay separación development/production.
El comportamiento cambia según las variables de entorno del proceso.
Ver .env.example (si existe) o el docker-compose.yml para las variables esperadas.

Decisiones de diseño:
- Sin django.contrib.auth ni django.contrib.admin: la gestión de usuarios
  es responsabilidad del sistema externo; este servicio no tiene sesiones.
- Sin SessionMiddleware ni AuthenticationMiddleware: la API es stateless,
  la autenticación se hace con JWT en cada petición.
- JWTAuthentication decodifica sin verificar firma porque este servicio
  no tiene acceso a la clave privada del sistema externo.
"""
import os
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'django_celery_beat',
    'apps.catalog',
    'apps.helpdesks',
    'apps.sla',
    'apps.classifier',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'helpdesk_dev'),
        'USER': os.environ.get('DB_USER', 'helpdesk'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'helpdesk'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# Storage configuration: different paths for server vs Docker
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')  # 'local' or 'docker'
if ENVIRONMENT == 'docker':
    MEDIA_ROOT = os.environ.get('MEDIA_ROOT_DOCKER', '/app/media')
else:
    MEDIA_ROOT = os.environ.get('MEDIA_ROOT_LOCAL', '/var/data/calidadpro/media')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'True') == 'True'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'recalculate-queue-scores': {
        'task': 'apps.sla.tasks.recalculate_queue_scores',
        'schedule': 900,  # every 15 minutes
    },
    'process-queue-business-start': {
        'task': 'apps.sla.tasks.process_all_queues',
        'schedule': crontab(hour=8, minute=30, day_of_week='1-5'),  # Mon-Fri 08:30
    },
    'train-classifier': {
        'task': 'apps.classifier.tasks.train_classifier',
        'schedule': crontab(hour=2, minute=0),  # diario a las 2am
    },
}

# Clasificador: máximo de feedbacks por usuario por día calendario.
# Los que exceden se guardan con rate_limited=True y no influyen en el entrenamiento.
CLASSIFIER_DAILY_FEEDBACK_LIMIT = int(os.environ.get('CLASSIFIER_DAILY_FEEDBACK_LIMIT', '20'))
