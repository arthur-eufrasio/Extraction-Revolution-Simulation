import os


def clean_files():
    key_words_to_delete = ["acis", "rpy", ".rec"]
    for file_name in os.listdir(os.getcwd()):
        file_path = os.path.join(os.getcwd(), file_name)

        if os.path.isfile(file_path) and any(palavra in file_name for palavra in key_words_to_delete):
            try:
                os.remove(file_path)
                print(f"Removed: {file_name}")
            except Exception as e:
                print(f"[ERROR] File {file_name} could not be removed: {e}")