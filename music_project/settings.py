# music_project/settings.py
import os
from pathlib import Path

import dj_database_url
import environ
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

# --------------------------------------------------------------------------------------
# Base paths & environment
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env via both python-dotenv and django-environ
load_dotenv()  # loads environment from .env into process env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))  # also parse .env file

# --------------------------------------------------------------------------------------
# Django core settings
# --------------------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="django-insecure-temp-key")  # override in .env

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
        "music-archiver-498e27441f42.herokuapp.com",
    ],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://127.0.0.1",
        "http://localhost",
        "https://127.0.0.1",
        "https://localhost",
        "https://music-archiver-498e27441f42.herokuapp.com",
    ],
)

# Messages -> Bootstrap mapping
MESSAGE_TAGS = {messages.ERROR: "danger"}

# --------------------------------------------------------------------------------------
# Apps
# --------------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django_countries",
    # Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # Forms
    "crispy_forms",
    "crispy_bootstrap5",
    # Cloudinary
    "cloudinary_storage",
    "cloudinary",
    # Local apps
    "tracks",
    "album.apps.AlbumConfig",
    "plans",
    "basket",
    "home_page",
    "profile_page",
    "checkout",
    "ratings",
    "save_system",
    "follow_system",
    "playlist",
    "cloud_connect",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Login/Logout redirects
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"  # Django auth
ACCOUNT_LOGOUT_REDIRECT_URL = "home"  # Allauth (kept alongside)

# ---------------- Google Auth config ---------------- #
# OAuth config (dev URLs shown; change in prod)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://music-archiver-498e27441f42.herokuapp.com/cloud/callback/gdrive/",
)
GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]
# ---------------- Allauth config ---------------- #
ACCOUNT_EMAIL_VERIFICATION = "none"

# ✅ allow both username and email login
ACCOUNT_LOGIN_METHODS = {"username", "email"}

# Crispy
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# --------------------------------------------------------------------------------------
# Middleware / URLs / Templates / WSGI
# --------------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "music_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "basket.contexts.basket_contents",
                "profile_page.context_processors.user_profile",
                "save_system.context_processors.user_albums_for_save",
                "playlist.context_processors.playlist_membership",
                "tracks.context_processors.ui_track_state",
            ],
            "libraries": {
                "rating_extras": "ratings.templatetags.rating_extras",
            },
        },
    },
]

WSGI_APPLICATION = "music_project.wsgi.application"

# --------------------------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------------------
# Static & Media
# --------------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# For collectstatic in production (served by your web server or CDN)
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

# Use Cloudinary for all media (keep your existing logic)
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.environ.get("CLOUDINARY_API_KEY"),
    "API_SECRET": os.environ.get("CLOUDINARY_API_SECRET"),
    # allow audio/video/raw uploads, not just images
    "RESOURCE_TYPE": "auto",
}
MEDIA_ALLOW_NOT_IMAGE = True
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --------------------------------------------------------------------------------------
# Stripe (keep your logic; read from env)
# --------------------------------------------------------------------------------------
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
# webhook secret:
STRIPE_WH_SECRET = os.environ.get("STRIPE_WH_SECRET")

# --------------------------------------------------------------------------------------
# Security hardening toggled by DEBUG
# --------------------------------------------------------------------------------------
# Debug only locally
DEBUG = "DEVELOPMENT" in os.environ
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------------------
# Default primary key field
# --------------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------------------
# PostgreSQL Database Configs
# --------------------------------------------------------------------------------------

# Database: always use DATABASE_URL if it exists
DB_URL = os.environ.get("DATABASE_URL")
if DB_URL:
    DATABASES = {
        "default": dj_database_url.parse(DB_URL, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
