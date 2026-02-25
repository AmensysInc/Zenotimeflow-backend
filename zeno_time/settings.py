"""
Django settings for zeno_time project.
Production: set all DB_* and SECRET_KEY via environment; never commit .env.
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment: django-environ (recommended) or python-decouple / os.environ
# Load .env from project root when present. Never commit .env; use .env.example as template.
# ---------------------------------------------------------------------------
try:
    import environ
    env = environ.Env(
        DEBUG=(bool, False),
        SECRET_KEY=(str, ''),
        ALLOWED_HOSTS=(list, []),
        DB_NAME=(str, 'zenotimeflow_db'),
        DB_USER=(str, 'root'),
        DB_PASSWORD=(str, ''),
        DB_HOST=(str, 'localhost'),
        DB_PORT=(str, '3306'),
        CORS_ALLOWED_ORIGINS=(list, []),
    )
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        env.read_env(str(env_file))

    def config(key, default=None, cast=None):
        try:
            val = env(key, default=default)
        except Exception:
            val = os.environ.get(key, default)
        if cast is not None and val is not None:
            if cast is bool:
                val = str(val).lower() in ('true', '1', 'yes')
            else:
                val = cast(val)
        return val
except ImportError:
    try:
        from decouple import config
    except ImportError:
        def config(key, default=None, cast=None):
            val = os.environ.get(key, default)
            if cast is not None and val is not None:
                if cast is bool:
                    val = str(val).lower() in ('true', '1', 'yes')
                else:
                    val = cast(val)
            return val


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

def _split_list(val):
    if isinstance(val, list):
        return [s.strip() if isinstance(s, str) else str(s).strip() for s in val]
    return [s.strip() for s in str(val).split(',') if s.strip()]

_allowed_hosts = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,zenotimeflow.com,www.zenotimeflow.com',
    cast=_split_list
)
# Always allow internal hosts (Waitress / reverse-proxy / same-server calls)
for _h in ('localhost', '127.0.0.1', 'waitress.invalid'):
    if _h not in _allowed_hosts:
        _allowed_hosts.append(_h)
ALLOWED_HOSTS = _allowed_hosts

# IIS + ARR reverse proxy: trust X-Forwarded-Host and X-Forwarded-Proto (HTTPS)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'channels',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'scheduler',
    'calendar_app',
    'tasks',
    'habits',
    'focus',
    'templates',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zeno_time.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'zeno_time.wsgi.application'
ASGI_APPLICATION = 'zeno_time.asgi.application'


# Database Configuration for SaaS Multi-Tenant Architecture
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
#
# Production (SaaS): USE_SQLITE=0 → MySQL with zenotimeflow_db
# Development: USE_SQLITE=1 → SQLite (fallback when MySQL unavailable)
#
# MySQL Configuration:
# - Database: zenotimeflow_db (created via MySQL client)
# - Engine: InnoDB (ACID compliance, foreign keys, row-level locking)
# - Charset: utf8mb4 (full Unicode support including emojis)
# - SQL Mode: STRICT_TRANS_TABLES (data integrity)
# - Connection pooling: CONN_MAX_AGE (0=close after request, 60+ for production)
USE_SQLITE = config('USE_SQLITE', default=True, cast=bool)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # MySQL configuration for production SaaS deployment
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='zenotimeflow_db'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                # UTF-8 with full Unicode support (emojis, international chars)
                'charset': 'utf8mb4',
                # Connection timeout (seconds)
                'connect_timeout': 10,
                # Strict SQL mode for data integrity
                # Note: NO_AUTO_CREATE_USER removed (deprecated in MySQL 8.0.11+)
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
                # Use InnoDB engine (recommended for Django/FK support)
                # Note: Table engine is set via migrations; this ensures compatibility
            },
            # Connection pooling: 0=close after request (dev), 60-600 for production
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=0, cast=int),
            # Test database isolation (prevents accidental data loss)
            'TEST': {
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Settings
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:6173,http://localhost:8080,http://localhost:8081,http://127.0.0.1:6173,http://127.0.0.1:8080,http://127.0.0.1:8081',
    cast=_split_list
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Channels Configuration (for WebSocket/real-time features)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Email Configuration (for welcome emails, etc.)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@zenotimeflow.com')

