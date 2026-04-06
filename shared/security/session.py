# shared/security/session.py

from typing import Optional, Dict


class Session:
    _access_token: Optional[str] = None
    _user: Optional[Dict] = None

    @classmethod
    def start(cls, token: str, user: Dict):
        cls._access_token = token
        cls._user = user

    @classmethod
    def clear(cls):
        cls._access_token = None
        cls._user = None

    @classmethod
    def token(cls) -> Optional[str]:
        return cls._access_token

    @classmethod
    def user(cls) -> Optional[Dict]:
        return cls._user

    @classmethod
    def branch_id(cls) -> Optional[int]:
        return cls._user.get("branch_id") if cls._user else None

    @classmethod
    def role(cls) -> Optional[str]:
        return cls._user.get("role") if cls._user else None

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls._access_token is not None and cls._user is not None