import base64
import io
import zipfile

from appConfig import firebaseConfig, firestoreConfig
from func.FirebaseAuthedSession import authed_session

PROJECT_ID = firebaseConfig["projectId"]
COLLECTION_NAME = "mail"
DATABASE_ID = firestoreConfig["kkiDatabaseId"]

def create_zip_in_memory(files_data):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files_data:
            zf.writestr(file["file_name"], file["file_data"])
    return zip_buffer.getvalue()


def sendWithEmail(to_email, subject, html_body, text_body, attachments=None):
    if attachments is None:
        attachments = []

    processed_attachments = []
    for att in attachments:
        b64_str = base64.b64encode(att['content']).decode('utf-8')
        processed_attachments.append({
            "filename": att['filename'],
            "content": b64_str,
            "encoding": "base64"
        })

    payload_data = {
        "to": [to_email],
        "message": {
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "attachments": processed_attachments
        }
    }

    def to_firestore_value(value):
        if isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, (int, float)):
            return {"integerValue": str(value)} if isinstance(value, int) else {"doubleValue": value}
        elif isinstance(value, bool):
            return {"booleanValue": value}
        elif isinstance(value, dict):
            return {"mapValue": {"fields": {k: to_firestore_value(v) for k, v in value.items()}}}
        elif isinstance(value, list):
            return {"arrayValue": {"values": [to_firestore_value(v) for v in value]}}
        elif value is None:
            return {"nullValue": None}
        return {"stringValue": str(value)}

    firestore_payload = {
        "fields": {k: to_firestore_value(v) for k, v in payload_data.items()}
    }

    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DATABASE_ID}/documents/{COLLECTION_NAME}"

    try:
        response = authed_session.post(url, json=firestore_payload)
        response.raise_for_status()
        return True, "Email queued successfully!"
    except Exception as e:
        if 'response' in locals() and hasattr(response, 'text'):
            print("Firestore Error Response:", response.text)
        return False, str(e)