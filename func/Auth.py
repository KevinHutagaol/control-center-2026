import base64
import hashlib
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from pandas.io.sas.sas_constants import column_name_text_subheader_offset

import func.FirebaseAuthedSession
from appConfig import firebaseConfig, oAuthConfig
from func.FirebaseAuthedSession import authed_session

FIREBASE_API_KEY = firebaseConfig["apiKey"]
CLIENT_ID = oAuthConfig["clientId"]

def generatePKCE():
    verifier = secrets.token_urlsafe(64)
    verifier_hashed = hashlib.sha256(verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(verifier_hashed).decode('ascii').replace('=','')
    return verifier, code_challenge


class OAuthHandler(BaseHTTPRequestHandler):
    def _send_html(self, status_code, title, message, color="#2ecc71", icon="✓"):
        self.send_response(status_code)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f6; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.08); text-align: center; max-width: 400px; width: 90%; }}
                .icon {{ font-size: 50px; color: white; background: {color}; width: 80px; height: 80px; line-height: 80px; border-radius: 50%; margin: 0 auto 20px; }}
                h1 {{ color: #2c3e50; margin: 0 0 10px; font-size: 24px; }}
                p {{ color: #7f8c8d; line-height: 1.5; margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">{icon}</div>
                <h1>{title}</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._send_html(
                200,
                "Login Successful!",
                "Authentication was successful. You can now close this tab and return to the application."
            )
        else:
            self._send_html(
                400,
                "Authentication Failed",
                "No authorization code was found in the request. Please try logging in again.",
                color="#e74c3c",
                icon="✕"
            )


def getOAuthCode(server, auth_url):
    print("Openning Browser for Login")
    webbrowser.open(auth_url)
    server.handle_request()
    return getattr(server, 'auth_code', None)


def runGoogleAuth():
    code_verifier, code_challenge = generatePKCE()

    server = HTTPServer(('127.0.0.1', 0), OAuthHandler)
    assigned_port = server.server_address[1]
    dynamic_redirect_uri = f"http://127.0.0.1:{assigned_port}"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": dynamic_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    auth_code = getOAuthCode(server, auth_url)

    if not auth_code:
        print("Failed to get auth code.")
        return False, "Authentication Failed: Failed to get OAuth code"

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": CLIENT_ID,
        "code": auth_code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": dynamic_redirect_uri
    }

    token_res = requests.post(token_url, data=token_data).json()
    google_id_token = token_res.get("id_token")

    if not google_id_token:
        print("Unable to get Google ID Token: ", token_res)
        return False, "Authentication Failed: Unable to get Google ID Token"

    firebase_auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    firebase_auth_payload = {
        "requestUri": "http://localhost",
        "postBody": f"id_token={google_id_token}&providerId=google.com",
        "returnSecureToken": True,
        "returnIdpCredential": True
    }

    success = getFirebaseId(firebase_auth_url, firebase_auth_payload)

    return success, "" if success else "Unable to acquire Firebase ID, your Email might not be whitelisted for this application"


def runPasswordAuth(email, password):
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    return getFirebaseId(auth_url, payload)


def getFirebaseId(url, data):
    firebase_res = requests.post(url, json=data)
    data = firebase_res.json()

    if firebase_res.status_code != 200:
        print("Login Failed:", data.get('error', {}).get('message', 'Unknown error'))
        return False

    if data.get('idToken') is None:
        return False

    print("Login Success")
    # print("Firebase ID Token:", data['idToken'])
    # print("Refresh Token:", data['refreshToken'])
    authed_session.set_credentials(data['refreshToken'], data['idToken'], int(float(data['expiresIn'])))

    return True


class AuthWorker(QObject):
    finished = pyqtSignal(bool, dict)

    def __init__(self):
        super().__init__()


    @pyqtSlot()
    def loginWithGoogle(self):
        try:
            success, msg = runGoogleAuth()
            if success:
                self.finished.emit(True, {"msg": "Success"})
            else:
                self.finished.emit(False, {"msg": msg})
        except Exception as e:
            self.finished.emit(False, {"msg": str(e)})

    @pyqtSlot(str, str)
    def loginWithPassword(self, email, password):
        try:
            success = runPasswordAuth(email, password)
            if success:
                self.finished.emit(True, {"msg": "Success"})
            else:
                self.finished.emit(False, {"msg": "Invalid Email or Password"})
        except Exception as e:
            self.finished.emit(False, {"msg": str(e)})



