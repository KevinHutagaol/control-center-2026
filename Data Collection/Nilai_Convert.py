import pandas as pd
import json

# Membaca file CSV
# Menggunakan delimiter ';' sesuai dengan format yang terdeteksi
df = pd.read_csv(
    'Data Collection/Nilai.csv', 
    delimiter=';',
    dtype={
        'NPM': str, 
    })

# Mengganti nama kolom agar lebih jelas
# Asumsi urutan kolom adalah NPM, Nama, Pass, Role
df.columns = ['NPM', 'Nama', 'Pretest', '(Modul 2&3) Tugas Pendahuluan', '(Modul 2&3) Borang Simulasi', '(Modul 2&3) Borang Analisis', '(Modul 2&3) Tugas Tambahan', '(Modul 4) Tugas Pendahuluan', '(Modul 4) Borang Simulasi', '(Modul 4) Borang Analisis', '(Modul 4) Tugas Tambahan', '(Modul 5) Tugas Pendahuluan', '(Modul 5) Borang Simulasi', '(Modul 5) Borang Analisis', '(Modul 5) Tugas Tambahan', '(Modul 6) Tugas Pendahuluan', '(Modul 6) Borang Simulasi', '(Modul 6) Borang Analisis', '(Modul 6) Tugas Tambahan', '(Modul 7) Tugas Pendahuluan', '(Modul 7) Borang Simulasi', '(Modul 7) Borang Analisis', '(Modul 7) Tugas Tambahan', '(Modul 8) Tugas Pendahuluan', '(Modul 8) Borang Simulasi', '(Modul 8) Borang Analisis', '(Modul 8) Tugas Tambahan', '(Modul 9&10) Tugas Pendahuluan', '(Modul 9&10) Borang Simulasi', '(Modul 9&10) Borang Analisis', '(Modul 9&10) Tugas Tambahan', '(Modul 11) Project Concept', '(Modul 11) Project Complexity', '(Modul 11) Project Readability', '(Modul 11) Scene Arragement', '(Modul 11) Project Explanation', '(Modul 11) Program Explanation', '(Modul 11) Simulation', 'Post-Test Modul 2&3', 'Post-Test Modul 4', 'Post-Test Modul 5', 'Post-Test Modul 6', 'Post-Test Modul 7', 'Post-Test Modul 8', 'Post-Test Modul 9&10', 'Bonus']

# 1. Bersihkan Kolom NPM: Ganti '.0' dengan string kosong
#    Ini memastikan NPM tetap menjadi string tanpa .0 di belakangnya
df['NPM'] = df['NPM'].astype(str).str.replace(r'\.0$', '', regex=True)

# Membuat struktur data Python (dictionary) sesuai permintaan
akun_dict = {}
for index, row in df.iterrows():
    npm = row['NPM']
    akun_dict[npm] = {
        'Nama': row['Nama'],
        'Pretest': row['Pretest'],
        '(Modul 2&3) Tugas Pendahuluan': row['(Modul 2&3) Tugas Pendahuluan'],
        '(Modul 2&3) Borang Simulasi': row['(Modul 2&3) Borang Simulasi'],
        '(Modul 2&3) Borang Analisis': row['(Modul 2&3) Borang Analisis'],
        '(Modul 2&3) Tugas Tambahan': row['(Modul 2&3) Tugas Tambahan'],
        '(Modul 4) Tugas Pendahuluan': row['(Modul 4) Tugas Pendahuluan'],
        '(Modul 4) Borang Simulasi': row['(Modul 4) Borang Simulasi'],
        '(Modul 4) Borang Analisis': row['(Modul 4) Borang Analisis'],
        '(Modul 4) Tugas Tambahan': row['(Modul 4) Tugas Tambahan'],
        '(Modul 5) Tugas Pendahuluan': row['(Modul 5) Tugas Pendahuluan'],
        '(Modul 5) Borang Simulasi': row['(Modul 5) Borang Simulasi'],
        '(Modul 5) Borang Analisis': row['(Modul 5) Borang Analisis'],
        '(Modul 5) Tugas Tambahan': row['(Modul 5) Tugas Tambahan'],
        '(Modul 6) Tugas Pendahuluan': row['(Modul 6) Tugas Pendahuluan'],
        '(Modul 6) Borang Simulasi': row['(Modul 6) Borang Simulasi'],
        '(Modul 6) Borang Analisis': row['(Modul 6) Borang Analisis'],
        '(Modul 6) Tugas Tambahan': row['(Modul 6) Tugas Tambahan'],
        '(Modul 7) Tugas Pendahuluan': row['(Modul 7) Tugas Pendahuluan'],
        '(Modul 7) Borang Simulasi': row['(Modul 7) Borang Simulasi'],
        '(Modul 7) Borang Analisis': row['(Modul 7) Borang Analisis'],
        '(Modul 7) Tugas Tambahan': row['(Modul 7) Tugas Tambahan'],
        '(Modul 8) Tugas Pendahuluan': row['(Modul 8) Tugas Pendahuluan'],
        '(Modul 8) Borang Simulasi': row['(Modul 8) Borang Simulasi'],
        '(Modul 8) Borang Analisis': row['(Modul 8) Borang Analisis'],
        '(Modul 8) Tugas Tambahan': row['(Modul 8) Tugas Tambahan'],
        '(Modul 9&10) Tugas Pendahuluan': row['(Modul 9&10) Tugas Pendahuluan'],
        '(Modul 9&10) Borang Simulasi': row['(Modul 9&10) Borang Simulasi'],
        '(Modul 9&10) Borang Analisis': row['(Modul 9&10) Borang Analisis'],
        '(Modul 9&10) Tugas Tambahan': row['(Modul 9&10) Tugas Tambahan'],
        '(Modul 11) Project Concept': row['(Modul 11) Project Concept'],
        '(Modul 11) Project Complexity': row['(Modul 11) Project Complexity'],
        '(Modul 11) Project Readability': row['(Modul 11) Project Readability'],
        '(Modul 11) Scene Arragement': row['(Modul 11) Scene Arragement'],
        '(Modul 11) Project Explanation': row['(Modul 11) Project Explanation'],
        '(Modul 11) Program Explanation': row['(Modul 11) Program Explanation'],
        '(Modul 11) Simulation': row['(Modul 11) Simulation'],
        'Post-Test Modul 2&3': row['Post-Test Modul 2&3'],
        'Post-Test Modul 4': row['Post-Test Modul 4'],
        'Post-Test Modul 5': row['Post-Test Modul 5'],
        'Post-Test Modul 6': row['Post-Test Modul 6'],
        'Post-Test Modul 7': row['Post-Test Modul 7'],
        'Post-Test Modul 8': row['Post-Test Modul 8'],
        'Post-Test Modul 9&10': row['Post-Test Modul 9&10'],
        'Post-Test Bonus': row['Bonus']
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
    'Nilai': {npm: akun_dict[npm] for npm in first_10_npms}
}

print(json.dumps(example_output, indent=4))

with open('Nilai.json', 'w') as f:
    f.write(json_output)