import os
import subprocess
import re

# This regex matches "import anyname_rc" or "from . import anyname_rc"
RESOURCE_IMPORT_PATTERN = re.compile(r"import .*_rc")

def main():
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".ui"):
                ui_path = os.path.join(root, file)
                py_path = os.path.join(root, f"ui_{file.replace('.ui', '.py')}")

                subprocess.run(["pyuic5", ui_path, "-o", py_path])

                with open(py_path, "r") as f:
                    lines = f.readlines()

                with open(py_path, "w") as f:
                    removed_count = 0
                    for line in lines:
                        if not RESOURCE_IMPORT_PATTERN.match(line.strip()):
                            f.write(line)
                        else:
                            removed_count += 1

                print(f"Done: {file} -> {os.path.basename(py_path)} (Cleaned {removed_count} imports)")


if __name__ == "__main__":
    main()