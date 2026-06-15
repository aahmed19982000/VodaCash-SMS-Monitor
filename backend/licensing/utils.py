import re

def normalize_egyptian_phone(number: str) -> str:
    if not number:
        return ""
    # Remove all spaces and dashes
    number = re.sub(r'[\s\-]', '', number)
    
    # Strip leading +2 or 002
    if number.startswith('+2'):
        number = number[2:]
    elif number.startswith('002'):
        number = number[3:]
    # Handle the case where user typed 201xxxxxxxxxx (12 digits)
    elif number.startswith('201') and len(number) == 12:
        number = number[1:]
    # Handle case where user omitted the leading zero: 1xxxxxxxxxx (10 digits)
    elif number.startswith('1') and len(number) == 10:
        number = '0' + number
        
    return number
