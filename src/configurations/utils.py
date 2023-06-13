import enum


class CookieSettings:
    def __init__(
        self,
        name: str,
        max_age: int = None,
        path: str = "/",
        domain: str = None,
        secure: bool = True,
        httponly: bool = False,
        samesite: str = "Lax",
    ) -> None:
        self.name = name
        self.max_age = max_age
        self.path = path
        self.domain = domain
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite


class EnvMode(enum.Enum):
    TEST = enum.auto()
    DEV = enum.auto()
    QA = enum.auto()
    PROD = enum.auto()
    DEMO = enum.auto()


def add_ending_slash(url: str) -> str:
    if url.endswith("/"):
        return url
    return f"{url}/"


def remove_ending_slash(url: str) -> str:
    if url.endswith("/"):
        return url[:-1]
    return url
