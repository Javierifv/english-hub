import sqlite3
import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('data/duohub.db')
c = conn.cursor()

sample_checks = [
    (101, 'https://www.robinsoncrusoeinlevels.com/level1/chapter2/'),
    (115, 'https://www.robinsoncrusoeinlevels.com/level1/chapter16/'),
    (131, 'https://www.robinsoncrusoeinlevels.com/level2/chapter1/'),
    (145, 'https://www.robinsoncrusoeinlevels.com/level2/chapter15/'),
    (162, 'https://www.robinsoncrusoeinlevels.com/level3/chapter1/'),
    (177, 'https://www.robinsoncrusoeinlevels.com/level3/chapter16/')
]

for row_id, url in sample_checks:
    c.execute('SELECT title, content FROM readings WHERE id = ?', (row_id,))
    row = c.fetchone()
    db_title, db_content = row[0], row[1]
    
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
    with urllib.request.urlopen(req, context=ctx) as r:
        soup = BeautifulSoup(r.read(), 'html.parser')
        entry = soup.find('div', class_='entry-content')
        ps = [p.get_text().strip() for p in entry.find_all('p') if p.get_text().strip()]
        clean_ps = [p for p in ps if not any(x in p.lower() for x in ['buy the whole', 'next chapter', 'robinson crusoe in levels is a book', 'students can read', 'level 1', 'level 2', 'level 3', '.mp3'])]
        web_story = '\n\n'.join(clean_ps)
        
    diff = len(web_story) - len(db_content)
    print(f"ID {row_id} - {db_title}: DB len={len(db_content)}, Web len={len(web_story)}, diff={diff}")
    if abs(diff) > 20:
        print("  Web first 150 chars:", repr(web_story[:150]))
        print("  DB  first 150 chars:", repr(db_content[:150]))
