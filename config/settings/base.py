from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = 'change-me-in-production'

DEBUG = False

ALLOWED_HOSTS = []

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
]

LOCAL_APPS = [
    'domains.users',
    'domains.help_desk',
    'domains.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_LIBS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'shared.exceptions.custom_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'shared.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ── Clasificador de tickets ────────────────────────────────────────────────────
# Configurable por deployment. Las keywords determinan la categoría sugerida.
CLASSIFIER_CATEGORIES = {
    'infrastructure': [
        'servidor', 'server', 'red', 'network', 'vpn', 'firewall',
        'internet', 'wifi', 'storage', 'almacenamiento', 'nube', 'cloud',
    ],
    'software': [
        'aplicacion', 'aplicación', 'error', 'falla', 'crash', 'instalar',
        'actualizar', 'licencia', 'software', 'programa', 'sistema',
    ],
    'hardware': [
        'impresora', 'teclado', 'mouse', 'monitor', 'equipo', 'computadora',
        'laptop', 'telefono', 'teléfono', 'escaner', 'escáner',
    ],
    'access': [
        'contraseña', 'password', 'acceso', 'permiso', 'usuario', 'cuenta',
        'bloqueo', 'login', 'sesion', 'sesión', 'autenticacion',
    ],
    'other': [],
}

CLASSIFIER_PRIORITIES = {
    'critical': [
        'caido', 'caída', 'urgente', 'produccion', 'producción',
        'todos', 'bloqueado', 'sin servicio', 'no funciona nada',
    ],
    'high': [
        'lento', 'intermitente', 'degradado', 'varios usuarios', 'equipo completo',
    ],
    'medium': [
        'problema', 'falla', 'no funciona', 'issue',
    ],
    'low': [
        'pregunta', 'solicitud', 'como', 'cómo', 'informacion', 'información',
    ],
}
