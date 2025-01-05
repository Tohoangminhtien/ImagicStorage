import re

def contains_special_characters(string: str) -> bool:
    # Biểu thức chính quy để kiểm tra ký tự không phải là chữ cái và chữ số
    return bool(re.search(r'[^a-zA-Z0-9]', string))  # Cho phép chữ cái