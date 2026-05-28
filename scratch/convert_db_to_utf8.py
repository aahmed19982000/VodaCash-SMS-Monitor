# scratch/convert_db_to_utf8.py
filepath = 'desktop/db/database.py'

with open(filepath, 'r', encoding='windows-1256') as f:
    content = f.read()

# Let's add an explicit UTF-8 encoding header to the top of the file just in case,
# but UTF-8 is default in Python 3.
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Successfully converted database.py to UTF-8!")
