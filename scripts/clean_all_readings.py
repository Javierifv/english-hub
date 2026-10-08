import sqlite3
import re
import urllib.request
import ssl
from bs4 import BeautifulSoup

conn = sqlite3.connect('data/duohub.db')
cursor = conn.cursor()

# 1. Fetch proper content for ID 139 (Level 2 Chapter 9)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
url = 'https://www.robinsoncrusoeinlevels.com/level2/chapter9/'
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')
inners = soup.find_all('div', class_='et_pb_text_inner')
# inners[1] and inners[2] contain the story
story_139 = inners[1].get_text().strip() + "\n\n" + inners[2].get_text().strip()
cursor.execute('UPDATE readings SET content = ? WHERE id = 139', (story_139,))
print("Updated ID 139 content from website.")

# 2. Clean ALL 93 readings
cursor.execute('SELECT id, title, content FROM readings')
rows = cursor.fetchall()

cleaned_total = 0
for rid, title, content in rows:
    # Remove Divi tags
    clean = re.sub(r'\[/?et_pb_[^\]]*\]', '', content)
    
    # Cut off WORDS FROM / WORDS FOR CHAPTER
    clean = re.split(r'words\s+(?:from|for)\s+chapter', clean, flags=re.IGNORECASE)[0]
    
    # Remove trailing 'aaa', extra whitespace
    clean = re.sub(r'\s*aaa\s*$', '', clean, flags=re.IGNORECASE)
    clean = clean.strip()
    
    # Normalize multiple newlines
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    
    if clean != content:
        cursor.execute('UPDATE readings SET content = ? WHERE id = ?', (clean, rid))
        cleaned_total += 1

conn.commit()
print(f"Successfully cleaned {cleaned_total} readings out of {len(rows)}!")
conn.close()
