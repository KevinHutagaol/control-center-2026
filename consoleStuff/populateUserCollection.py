import secrets

import pandas as pd
import firebase_admin
from firebase_admin import credentials, auth, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def createUserCollection(email, displayName, role):
    user_record = auth.create_user(
        email=email,
        password = secrets.token_urlsafe(32)
    )

    uid = user_record.uid
    print(f"Successfully created auth user: {email} ({uid})")

    user_ref = db.collection("users").document(uid)

    user_ref.set({
        "uid": uid,
        "email": email,
        "displayName": displayName,
        "role": role,
        "createdAt": firestore.firestore.SERVER_TIMESTAMP,
        "userData": {}
    })

    user_ref.collection("userData").document("profile").set({
        "bio": "",
        "preferences": {}
    })

    print(f"Successfully created user database entry: {email} ({uid})")


df = pd.read_excel("Database Praktikum KKI Teknik Kendali (Responses).xlsx")

print(df['Akun Gmail Utama'])
