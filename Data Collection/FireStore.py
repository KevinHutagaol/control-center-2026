import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# --- KONFIGURASI ---
# Ganti dengan path ke file service account JSON Anda
FIREBASE_CRED_PATH = 'FirebaseDataPraktikan.json' 
# Nama Koleksi (Collection) di Firestore tempat data akan disimpan
COLLECTION_NAME = 'Nilai'
# Nama file JSON yang berisi data Anda
DATA_FILE = 'Data Collection/Nilai.json'
# --- END KONFIGURASI ---

def import_json_to_firestore():
    # 1. Inisialisasi Firebase
    print("1. Menginisialisasi Firebase...")
    try:
        if not os.path.exists(FIREBASE_CRED_PATH):
            raise FileNotFoundError(f"File credentials tidak ditemukan di: {FIREBASE_CRED_PATH}")
            
        # Initialize aplikasi, Firestore tidak memerlukan databaseURL
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        # Cek apakah aplikasi sudah diinisialisasi
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        # Mendapatkan instance Firestore client
        db = firestore.client()
        print("Firebase dan Firestore client berhasil diinisialisasi.")
    except Exception as e:
        print(f"ERROR: Gagal inisialisasi Firebase. Pastikan file credentials benar dan valid. Error: {e}")
        return

    # 2. Memuat Data dari JSON
    print(f"2. Memuat data dari {DATA_FILE}...")
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Mengambil objek 'akun' yang berisi semua entri NPM
            # Nama kunci di file Anda mungkin 'Account' atau 'akun', kita cek kedua-duanya
            praktikan_data = data.get('akun') or data.get('Account')
            
            if not praktikan_data:
                print("ERROR: Struktur JSON tidak valid. Tidak ditemukan kunci 'akun' atau 'Account' di root.")
                return
            print(f"Ditemukan {len(praktikan_data)} entri praktikan untuk diimport.")
    except FileNotFoundError:
        print(f"ERROR: File data {DATA_FILE} tidak ditemukan.")
        return
    except json.JSONDecodeError:
        print(f"ERROR: Gagal membaca file JSON. Pastikan formatnya benar.")
        return

    # 3. Menulis Data ke Firestore menggunakan Batch
    print(f"3. Memulai proses batch writing ke Koleksi '{COLLECTION_NAME}'...")
    
    # Gunakan batch untuk menulis banyak dokumen secara efisien (max 500 operasi per batch)
    batch = db.batch()
    count = 0
    
    for npm, user_data in praktikan_data.items():
        # Setiap NPM (kunci) menjadi ID Dokumen unik
        doc_ref = db.collection(COLLECTION_NAME).document(npm)
        
        # Menambahkan operasi 'set' ke batch
        # user_data berisi Nama, Pass, Role, Kelompok, Nilai, dll.
        batch.set(doc_ref, user_data)
        count += 1
        
        if count % 499 == 0:
            batch.commit()
            print(f"    - Berhasil commit {count} dokumen...")
            batch = db.batch() # Mulai batch baru

    # Commit batch terakhir
    batch.commit()
    print("\n✅ Proses import selesai!")
    print(f"Total {count} dokumen berhasil diimpor ke Koleksi '{COLLECTION_NAME}' di Cloud Firestore.")

if __name__ == '__main__':
    import_json_to_firestore()