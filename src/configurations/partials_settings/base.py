from pathlib import Path

from environs import Env

from configurations.utils import EnvMode, add_ending_slash, remove_ending_slash  # noqa

env = Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)
ENV_MODE = env.enum("ENV_MODE", default="PROD", type=EnvMode)


# App distribution
WSGI_APPLICATION = "configurations.wsgi.application"
APPEND_SLASH = True
PREPEND_WWW = False
