from enum import Enum
from enum import auto
from typing import Final
from typing import NamedTuple
from typing import final


@final
class SmtpCryptoKind(Enum):
    NONE = auto()
    TLS = auto()
    SSL = auto()

    @classmethod
    def from_string(cls, value: str) -> "SmtpCryptoKind":
        match value.strip().lower():
            case "":
                return cls.NONE
            case "tls":
                return cls.TLS
            case "ssl":
                return cls.SSL
            case _:
                msg: Final = f"Unknown SMTP crypto kind: {value}"
                raise ValueError(msg)


@final
class SmtpSettings(NamedTuple):
    host: str
    port: int
    username: str
    password: str
    crypto: SmtpCryptoKind
    from_address: str
