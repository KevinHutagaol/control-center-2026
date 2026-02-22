import time
import requests
from appConfig import firebaseConfig

FIREBASE_API_KEY = firebaseConfig["apiKey"]

class FirebaseAuthedSession(requests.Session):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.refresh_token = None
        self.id_token = None
        self.expires_at = 0

    def set_credentials(self, refresh_token: str, id_token: str, expires_in: int = 3600):
        self.refresh_token = refresh_token
        self.id_token = id_token
        self.expires_at =  time.time() + expires_in - 60

    def refresh_id_token(self):
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        res = requests.post(url, data=data).json()
        self.id_token = res.get("id_token")
        self.expires_at = time.time() + int(res.get("expires_in", 3600)) - 60

    def request(self,method, url, *args, **kwargs):
        if not self.id_token or time.time() >= self.expires_at:
            self.refresh_id_token()

        kwargs.setdefault("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.id_token}"

        return super().request(method, url, *args, **kwargs)


authed_session: FirebaseAuthedSession = FirebaseAuthedSession(FIREBASE_API_KEY)
