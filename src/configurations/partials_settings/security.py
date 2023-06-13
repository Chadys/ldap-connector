from corsheaders.defaults import default_headers

from configurations.partials_settings.base import *  # noqa

# Security
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[], subcast=str)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[], subcast=str)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
# because message cookie aren't parameterised securely
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# django-cors-headers
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[], subcast=str)
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "CORS_ALLOWED_ORIGIN_REGEXES", default=[], subcast=str
)  # take care of backlash escaping when you add a value
CORS_ALLOW_CREDENTIALS = False  # prevent auth cookies
CORS_ALLOW_HEADERS = env.list(
    "CORS_ALLOW_HEADERS",
    default=(*list(default_headers),),
)

# django-csp
CSP_DEFAULT_SRC = env.list(
    "CSP_DEFAULT_SRC",
    default=[
        "'self'",
    ],
    subcast=str,
)
CSP_SCRIPT_SRC = env.list(
    "CSP_SCRIPT_SRC",
    default=[
        "'self'",
    ],
    subcast=str,
)
CSP_STYLE_SRC = env.list(
    "CSP_STYLE_SRC",
    default=[
        "'self'",
    ],
    subcast=str,
)
CSP_IMG_SRC = env.list(
    "CSP_IMG_SRC",
    default=[
        "'self'",
    ],
    subcast=str,
)
CSP_MEDIA_SRC = env.list("CSP_MEDIA_SRC", default=["'self'"], subcast=str)
CSP_FONT_SRC = env.list(
    "CSP_FONT_SRC",
    default=[
        "'self'",
    ],
    subcast=str,
)


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
