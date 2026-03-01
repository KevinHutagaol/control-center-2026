import base64
import hashlib
import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
import os
import sys
import shutil
import subprocess
import requests
import ssl

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from requests.adapters import HTTPAdapter
from urllib3 import Retry, PoolManager
from urllib3.util import ssl_

from appConfig import firebaseConfig, oAuthConfig
from func.FirebaseAuthedSession import authed_session

FIREBASE_API_KEY = firebaseConfig["apiKey"]
CLIENT_ID = oAuthConfig["clientId"]


class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        try:
            ctx.options |= 0x4
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        except AttributeError:
            pass

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

def get_safe_session():
    session = requests.Session()
    adapter = LegacySSLAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def openSandboxedBrowser(url):
    app_data_dir =  Path("./browser/.my_app_auth_cache").resolve()

    app_data_dir.mkdir(parents=True, exist_ok=True)
    user_data_path = str(app_data_dir)

    subprocess_kwargs = {
        'start_new_session': True,
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL
    }

    if sys.platform == 'win32':
        subprocess_kwargs['creationflags'] = 0x00000008
        del subprocess_kwargs['start_new_session']

    browsers = [
        ('chrome', ['google-chrome', 'chrome', 'google-chrome-stable'], f'--user-data-dir={user_data_path}'),
        ('edge', ['msedge', 'microsoft-edge', 'edge'], f'--user-data-dir={user_data_path}'),
        ('brave', ['brave-browser', 'brave'], f'--user-data-dir={user_data_path}'),
        ('firefox', ['firefox'], '-profile'),
    ]

    # macOS
    if sys.platform == 'darwin':
        candidates = [
            ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", f'--user-data-dir={user_data_path}'),
            ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", f'--user-data-dir={user_data_path}'),
        ]

        for exe_path, flag in candidates:
            if os.path.exists(exe_path):
                try:
                    subprocess.Popen([exe_path, flag, "--no-first-run", url], start_new_session=True)
                    return True
                except Exception:
                    continue

    #  Windows & Linux
    else:
        for browser_id, executable_names, flag in browsers:
            cmd_path = None

            for exe in executable_names:
                cmd_path = shutil.which(exe)
                if cmd_path:
                    break

            # Windows fallback search
            if not cmd_path and sys.platform == 'win32':
                prefixes = [
                    os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                    os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                    os.environ.get('LOCALAPPDATA', 'C:\\Users\\Default\\AppData\\Local')
                ]
                suffixes = {
                    'chrome': [r"Google\Chrome\Application\chrome.exe"],
                    'edge': [r"Microsoft\Edge\Application\msedge.exe"],
                    'brave': [r"BraveSoftware\Brave-Browser\Application\brave.exe"]
                    # no firefox on win
                }
                for prefix in prefixes:
                    for suffix in suffixes.get(browser_id, []):
                        p = os.path.join(prefix, suffix)
                        if os.path.exists(p):
                            cmd_path = p
                            break

            if cmd_path:
                try:
                    args = [cmd_path]

                    if browser_id == 'firefox':
                        args.extend(['-profile', user_data_path, '-no-remote', url])
                    else:
                        args.extend([flag, "--no-first-run", "--no-default-browser-check", url])

                    if sys.platform == 'win32':
                        subprocess.Popen(args, creationflags=0x00000008)
                    else:
                        subprocess.Popen(args, start_new_session=True)
                    return True
                except Exception as e:
                    print(f"Error launching {browser_id}: {e}")
                    continue

    print("Could not launch sandboxed browser. Using default.")
    webbrowser.open(url)
    return False

def logOutGoogleSession():
    logout_url = "https://accounts.google.com/Logout"

    print("Signing out of Google Session...")
    openSandboxedBrowser(logout_url)

def generatePKCE():
    verifier = secrets.token_urlsafe(64)
    verifier_hashed = hashlib.sha256(verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(verifier_hashed).decode('ascii').replace('=','')
    return verifier, code_challenge


class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

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
    openSandboxedBrowser(auth_url)
    server.handle_request()
    return getattr(server, 'auth_code', None)


def runGoogleAuth():
    code_verifier, code_challenge = generatePKCE()

    server = HTTPServer(('127.0.0.1', 0), OAuthHandler)
    try:
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
    finally:
        server.server_close()

    if not auth_code:
        print("Failed to get auth code.")
        return False, "Authentication Failed: Failed to get OAuth code"

    session = get_safe_session()

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": CLIENT_ID,
        "code": auth_code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": dynamic_redirect_uri
    }

    try:
        token_res = session.post(token_url, data=token_data).json()
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
    except Exception as e:
        print(e)
        return False, str(e)


def runPasswordAuth(email, password):
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    return getFirebaseId(auth_url, payload)


def configure_session_retries(session):
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)


def getFirebaseId(url, data):
    session = get_safe_session()

    try:
        firebase_res = session.post(url, json=data)
        res_data = firebase_res.json()

        if firebase_res.status_code != 200:
            print("Login Failed:", res_data.get('error', {}).get('message', 'Unknown error'))
            return False

        if res_data.get('idToken') is None:
            return False

        print("Login Success")

        global_adapter = LegacySSLAdapter()
        authed_session.mount("https://", global_adapter)

        configure_session_retries(authed_session)

        authed_session.set_credentials(
            res_data['refreshToken'],
            res_data['idToken'],
            res_data['localId'],
            int(float(res_data['expiresIn']))
        )

        return True
    except Exception as e:
        print(f"Error in getFirebaseId: {e}")
        return False


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



