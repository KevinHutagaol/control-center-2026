import base64
import hashlib
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot

import func.FirebaseAuthedSession
from firebaseConfig import firebaseConfig
from func.FirebaseAuthedSession import authed_session

FIREBASE_API_KEY = firebaseConfig["apiKey"]
CLIENT_ID = "830462089202-0jnppso4iihb42k7ek9lnla2nr4elunl.apps.googleusercontent.com"


def generatePKCE():
    verifier = secrets.token_urlsafe(64)
    verifier_hashed = hashlib.sha256(verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(verifier_hashed).decode('ascii').replace('=','')
    return verifier, code_challenge


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Login Successful!</h1><p>You can close this window and return to your app.</p>")
        else:
            self.send_response(400)
            self.end_headers()


def getOAuthCode(server, auth_url):
    print("Openning Browser for Login")
    webbrowser.open(auth_url)
    server.handle_request()
    return getattr(server, 'auth_code', None)


def runGoogleAuth():
    code_verifier, code_challenge = generatePKCE()

    server = HTTPServer(('localhost', 0), OAuthHandler)
    assigned_port = server.server_address[1]
    dynamic_redirect_uri = f"http://localhost:{assigned_port}"

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
        return False

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
        return

    firebase_auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    firebase_auth_payload = {
        "requestUri": "http://localhost",
        "postBody": f"id_token={google_id_token}&providerId=google.com",
        "returnSecureToken": True,
        "returnIdpCredential": True
    }

    firebase_res = requests.post(firebase_auth_url, json=firebase_auth_payload)
    data = firebase_res.json()

    if firebase_res.status_code == 200:
        print("Login Success")
        print("Firebase ID Token:", data['idToken'])
        print("Refresh Token:", data['refreshToken'])
        authed_session.set_credentials(data['refreshToken'], data['idToken'], data['refreshToken'])
        return True
    else:
        print("Login Failed:", data.get('error', {}).get('message', 'Unknown error'))
        return False


def runPasswordAuth(email, password):
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    firebase_res = requests.post(auth_url, json=payload)
    data = firebase_res.json()

    if firebase_res.status_code == 200:
        print("Login Success")
        print("Firebase ID Token:", data['idToken'])
        print("Refresh Token:", data['refreshToken'])
        authed_session.set_credentials(data['refreshToken'], data['idToken'], data['refreshToken'])
        return True
    else:
        print("Login Failed:", data.get('error', {}).get('message', 'Unknown error'))
        return False

class AuthWorker(QObject):
    finished = pyqtSignal(bool, dict)

    def __init__(self):
        super().__init__()


    @pyqtSlot()
    def loginWithGoogle(self):
        try:
            success = runGoogleAuth()
            if success:
                self.finished.emit(True, {"msg": "Success"})
            else:
                self.finished.emit(False, {"msg": "Google Auth Failed"})
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



