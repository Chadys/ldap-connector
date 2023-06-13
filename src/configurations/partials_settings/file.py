from .base import *

FTP_FOLDER = BASE_DIR / "data" / "ftp"
FTP_PROCESSED_FOLDER = FTP_FOLDER / "processed/%Y/%m/"

FTP_URL = env.str(
    "FTP_URL"
)  # expecting url in format <username>:<password>@<host>[:<port>]
__credentials, __host = FTP_URL.rsplit("@", 1)
__user, __pwd = __credentials.split(":", 1)
FTP_CONNEXION = {"host": __host, "user": __user, "passwd": __pwd}
FTP_USE_TLS = env.bool("FTP_USE_TLS", default=True)
FTP_CLEANUP_FILE = env.bool("FTP_CLEANUP_FILE", default=True)
