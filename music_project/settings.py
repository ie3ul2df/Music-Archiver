# music_project/settings.py
from pathlib import Path
import os
import environ
from dotenv import load_dotenv
from django.contrib.messages import constants as messages

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
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost"],
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
    "album",
    "plans",
    "basket",
    "home_page",
    "profile_page",
    "checkout",
    "ratings",
    "save_system",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Login/Logout redirects
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"                       # Django auth
ACCOUNT_LOGOUT_REDIRECT_URL = "home"               # Allauth (kept alongside)

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
            ],
        },
    },
]

WSGI_APPLICATION = "music_project.wsgi.application"

# --------------------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --------------------------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
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
