"""
Django settings for ecommerce_project project.
Production-hardened — all secrets loaded from .env via django-environ.
"""

import os
import sys
from pathlib import Path
import environ

# ─── Path ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Environment ────────────────────────────────────────────────
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'), override=False)

# ─── Core ───────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)

# Never use ['*'] in production — lock to your domains via .env
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['customiseclothing.in', 'www.customiseclothing.in'])

# ─── Applications ───────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'corsheaders',
    'rest_framework',
    'widget_tweaks',
    'store',
    'accounts',
]

# ─── Middleware ──────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce_project.wsgi.application'

# ─── Database (DATABASE_URL for PaaS, else PostgreSQL env vars) ──
_database_url = env('DATABASE_URL', default='')
if _database_url:
    # PaaS platforms (Railway/Render/Heroku) provide a single DATABASE_URL
    DATABASES = {'default': env.db_url('DATABASE_URL')}
    DATABASES['default']['CONN_MAX_AGE'] = 60
else:
    DATABASES = {
        'default': {
            'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
            'NAME': BASE_DIR / env('DB_NAME', default='db.sqlite3') if env.str('DB_ENGINE', default='').startswith('django.db.backends.sqlite3') else env('DB_NAME', default='customise_clothing'),
            'USER': env('DB_USER', default=''),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='127.0.0.1'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }

# ─── Password Validation ────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalization ───────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ─── Static & Media Files ──────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    # CompressedManifestStaticFilesStorage fails if referenced static files are
    # missing, which breaks deploys with pre-existing template issues.
    # CompressedStaticFilesStorage keeps compression but is forgiving.
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

PROJECT_STATIC_DIR = BASE_DIR / 'static'
STATICFILES_DIRS = [PROJECT_STATIC_DIR] if PROJECT_STATIC_DIR.exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── CORS ───────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://customiseclothing.in',
    'https://customiseclothing.in',
])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://customiseclothing.in',
    'https://customiseclothing.in',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://*.ngrok-free.dev',
])

# ─── Default primary key ───────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Auth Redirects ────────────────────────────────────────────
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
LOGIN_URL = '/accounts/login/'

# Master switch for public login/registration (OTP, email, or API).
# Set to True to re-enable the accounts UI and endpoints.
AUTH_ENABLED = env.bool('AUTH_ENABLED', default=False)

# ─── Django REST Framework & JWT ────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── Email ──────────────────────────────────────────────────────
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Customise Clothing <noreply@customiseclothing.com>')
EMAIL_SUBJECT_PREFIX = '[Customise Clothing] '
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@customiseclothing.com')

# ─── Razorpay ───────────────────────────────────────────────────
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_COMPANY_NAME = env('COMPANY_NAME', default='Customise Clothing')
RAZORPAY_COMPANY_LOGO = env('COMPANY_LOGO', default='https://customiseclothing.in/static/images/logo.png')
RAZORPAY_THEME_COLOR = env('COMPANY_THEME_COLOR', default='#6366f1')

# ─── Company / Contact Info ────────────────────────────────────
COMPANY_NAME = env('COMPANY_NAME', default='Customise Clothing')
CONTACT_PHONE = env('CONTACT_PHONE', default='+91 9114960778')
CONTACT_EMAIL = env('CONTACT_EMAIL', default='customiseclothingofficial@gmail.com')
CONTACT_SUPPORT_EMAIL = env('CONTACT_SUPPORT_EMAIL', default='help@customiseclothing.in')

# ─── Delivery Config ──────────────────────────────────────────
FREE_DELIVERY_THRESHOLD = env.str('FREE_DELIVERY_THRESHOLD', default='349.00')
DELIVERY_CHARGE = env.str('DELIVERY_CHARGE', default='25.00')
ORDER_DELIVERY_DAYS = env.int('ORDER_DELIVERY_DAYS', default=5)

# ─── Fallback Images ──────────────────────────────────────────
DEFAULT_PRODUCT_FALLBACK_IMAGE = env('DEFAULT_PRODUCT_FALLBACK_IMAGE', default='https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=400&q=80')
DEFAULT_CATEGORY_FALLBACK_IMAGE = env('DEFAULT_CATEGORY_FALLBACK_IMAGE', default='https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=150&h=150&fit=crop')

# ─── Security (production only) ────────────────────────────────
# `manage.py ...` commands run with plain http scheme locally; SECURE_SSL_REDIRECT
# and SECURE_PROXY_SSL_HEADER only apply to real requests, not management commands.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # Don't leak Django/Python versions in error pages
    ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h != '*']

# Behind Railway's proxy, make CSRF origin checks work for the app domain.
# Empty by default in local dev; set CSRF_TRUSTED_ORIGINS in the platform env.
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS]
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ─── Logging ────────────────────────────────────────────────────
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'store': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
