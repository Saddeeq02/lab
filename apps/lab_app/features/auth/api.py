# auth/api.py

from shared.net.api_client import ApiClient, ApiError


class AuthAPI:
    def __init__(self, api_client: ApiClient):
        self.api = api_client

    def login(self, username: str, password: str) -> dict:
        try:
            return self.api.post_json(
                "/api/auth/login",
                {
                    "username": username,
                    "password": password,
                },
            )
        except ApiError as e:
            if e.status_code == 401:
                raise Exception("Invalid username or password.")
            raise Exception(str(e))