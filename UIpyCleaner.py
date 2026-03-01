import os

def main():
    deleted_count = 0
    
    # Jalanin proses walk yang persis sama
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".ui"):
                # Bikin target path file .py yang mau dihapus
                py_path = os.path.join(root, f"ui_{file.replace('.ui', '.py')}")

                # Cek apakah file .py hasil generate itu beneran ada
                if os.path.exists(py_path):
                    try:
                        os.remove(py_path)
                        deleted_count += 1
                        print(f"Deleted: {os.path.basename(py_path)}")
                    except Exception as e:
                        print(f"Gagal menghapus {py_path}: {e}")

    print(f"\nSelesai! Berhasil membersihkan {deleted_count} file .py.")

if __name__ == "__main__":
    main()