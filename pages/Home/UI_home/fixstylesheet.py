import xml.etree.ElementTree as ET
import os

def add_border_none(ui_file_path):
    # Cek apakah file ada
    if not os.path.exists(ui_file_path):
        print(f"Error: File {ui_file_path} tidak ditemukan!")
        return

    # Parsing file XML (.ui)
    tree = ET.parse(ui_file_path)
    root = tree.getroot()
    modified_count = 0

    # Cari semua property yang namanya "styleSheet"
    for prop in root.findall('.//property[@name="styleSheet"]'):
        string_tag = prop.find('string')
        
        if string_tag is not None:
            current_style = string_tag.text or ""
            
            # Tambahkan border: none; jika belum ada
            if "border: none;" not in current_style and "border:none;" not in current_style:
                # Pastikan formatnya rapi
                new_style = current_style.strip()
                if new_style and not new_style.endswith(';'):
                    new_style += ';'
                
                string_tag.text = new_style + "\nborder: none;"
                modified_count += 1

    # Simpan kembali ke file .ui
    tree.write(ui_file_path, encoding='UTF-8', xml_declaration=True)
    print(f"Selesai! Berhasil menambahkan 'border: none;' ke {modified_count} widget di {ui_file_path}")

# --- Eksekusi Script ---
# Ganti 'ui_Login.ui' dengan nama file kamu jika berbeda
file_target = 'Main.ui' 
add_border_none(file_target)