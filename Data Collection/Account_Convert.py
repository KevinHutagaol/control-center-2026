import pandas as pd
import json

# Membaca file CSV
# Menggunakan delimiter ';' sesuai dengan format yang terdeteksi
df = pd.read_csv(
    'Data Collection\Account.csv', 
    delimiter=';',
    dtype={
        'NPM': str, 
        'Kelompok': str
    })

# Mengganti nama kolom agar lebih jelas
# Asumsi urutan kolom adalah NPM, Nama, Pass, Role
df.columns = ['NPM', 'Nama', 'Pass', 'Role', 'Kelompok']

# 1. Bersihkan Kolom NPM: Ganti '.0' dengan string kosong
#    Ini memastikan NPM tetap menjadi string tanpa .0 di belakangnya
df['NPM'] = df['NPM'].astype(str).str.replace(r'\.0$', '', regex=True)

# 2. Bersihkan Kolom Kelompok: Ganti '.0' dengan string kosong
df['Kelompok'] = df['Kelompok'].astype(str).str.replace(r'\.0$', '', regex=True)

# Membuat struktur data Python (dictionary) sesuai permintaan
akun_dict = {}
for index, row in df.iterrows():
    npm = row['NPM']
    akun_dict[npm] = {
        'Nama': row['Nama'],
        'Pass': row['Pass'],
        'Role': row['Role'],
        'Kelompok': row['Kelompok'],
    }

# Membungkus dictionary di dalam objek 'akun'
final_json_structure = {
    'Account': akun_dict
}

# Mengonversi ke string JSON (dengan indentasi untuk keterbacaan)
json_output = json.dumps(final_json_structure, indent=4)

# Menampilkan 10 entri pertama untuk contoh
print("10 Entri Pertama dari Struktur JSON:")
# Mengambil 10 kunci (NPM) pertama
first_10_npms = list(akun_dict.keys())[:10]

# Membuat struktur contoh untuk tampilan
example_output = {
    'Account': {npm: akun_dict[npm] for npm in first_10_npms}
}

print(json.dumps(example_output, indent=4))

with open('Account.json', 'w') as f:
    f.write(json_output)