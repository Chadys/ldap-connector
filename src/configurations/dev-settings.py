from django.contrib import messages

from .settings import *

INSTALLED_APPS.extend(
    [
        "django_extensions",
        "debug_toolbar",
        "django_watchfiles",
        "django_browser_reload",
        "django_linear_migrations",
    ]
)

MIDDLEWARE.insert(-1, "django_browser_reload.middleware.BrowserReloadMiddleware")
# MIDDLEWARE.insert(3, "debug_toolbar.middleware.DebugToolbarMiddleware")
# this is necessary because we can't predict INTERNAL_IPS on docker, solution given in
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#configure-internal-ips does not work
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# use rich to format error output
LOGGING.update(
    {
        "filters": {
            "require_debug_true": {
                "()": "django.utils.log.RequireDebugTrue",
            },
        },
        "formatters": {
            "rich": {"datefmt": "[%X]", "format": "%(message)s"},
        },
        "handlers": {
            "console": {
                "class": "rich.logging.RichHandler",
                "filters": ["require_debug_true"],
                "formatter": "rich",
                "level": "DEBUG",
                "rich_tracebacks": True,
                "tracebacks_show_locals": True,
                "show_path": False,
                "enable_link_path": False,
            },
        },
    }
)
