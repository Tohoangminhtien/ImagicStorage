import re
import os

def contains_special_characters(string: str) -> bool:
    # Biểu thức chính quy để kiểm tra ký tự không phải là chữ cái và chữ số
    return bool(re.search(r'[^a-zA-Z0-9.]', string))  # Cho phép chữ cái

def is_valid_image(file_path):
    allowed_extensions = ['png', 'jpeg', 'jpg']
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower().strip('.')
    if file_extension in allowed_extensions:
        return True
    else:
        return False