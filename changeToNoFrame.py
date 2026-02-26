import os
import fnmatch


def update_ui_files(root_dir):
    search_text = '<enum>QFrame::StyledPanel</enum>'
    replace_text = '<enum>QFrame::NoFrame</enum>'

    count = 0

    print(f"Scanning for .ui files in: {os.path.abspath(root_dir)}")

    for root, dirs, files in os.walk(root_dir):
        for filename in fnmatch.filter(files, '*.ui'):
            file_path = os.path.join(root, filename)

            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if replacement is needed
            if search_text in content:
                new_content = content.replace(search_text, replace_text)

                # Write the updated content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f"Updated: {file_path}")
                count += 1

    print(f"\nTask complete. Updated {count} files.")


if __name__ == "__main__":
    update_ui_files('.')