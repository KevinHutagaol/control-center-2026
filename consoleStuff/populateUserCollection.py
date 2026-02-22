import secrets

import pandas as pd
import firebase_admin
from firebase_admin import credentials, auth, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def createUserCollection(email, displayName, npm, regOrKki, year, group, role):
    try:
        user_record = auth.get_user_by_email(email)
        uid = user_record.uid
        print(f"User already exists in Auth: {email} ({uid})")
    except auth.UserNotFoundError:
        user_record = auth.create_user(
            email=email,
            password=secrets.token_urlsafe(32)
        )
        uid = user_record.uid
        print(f"Successfully created new auth user: {email} ({uid})")

    user_ref = db.collection("users").document(uid)
    doc_snapshot = user_ref.get()

    user_data = {
        "uid": uid,
        "email": email,
        "displayName": displayName,
        "npm": npm,
        "regOrKki": regOrKki,
        "year": year,
        "group": group,
        "role": role,
    }

    if not doc_snapshot.exists:
        user_data["createdAt"] = firestore.firestore.SERVER_TIMESTAMP
        user_ref.set(user_data)
        print(f"Created new database entry for: {email}")
    else:
        user_ref.update(user_data)
        print(f"Updated existing database entry for: {email}")

    # profile_ref = user_ref.collection("userData").document("profile")
    # if not profile_ref.get().exists:
    #     profile_ref.set({
    #         "bio": "",
    #         "preferences": {}
    #     })


df = pd.read_excel("Database Praktikum KKI Teknik Kendali (Responses).xlsx")

for data in df.to_dict('records'):
    email = data['Akun Gmail Utama']
    displayName = data['Nama Lengkap (Sesuai SIAKNG)']
    npm = str(data['NPM'])
    regOrKki = 'kki'
    year = 2024
    group = data['Nomor Kelompok']
    role = 'Mahasiswa'
    print(f"Creating user {email}: {displayName}, {npm}, {regOrKki}, {year}, {group}, {role}")
    createUserCollection(email, displayName, npm, regOrKki, year, group, role)
    print("")

createUserCollection('controllaboratory2026@gmail.com', 'Control Lab Ui', '0', 'reg', 0, 0, 'Admin')
createUserCollection('kevimanuel12345@gmail.com', 'Kevin Imanuel Hutagaol', '2306156763', 'reg', 2023, 0, 'Admin')
createUserCollection('haidaralghifari112@gmail.com', 'Haidar Al Ghifari', '2306266792', 'reg', 2023, 0, 'Admin')
