import urllib.request, ssl, sqlite3
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://robinsoncrusoeinlevels.com/level1/chapter2/', headers={'User-Agent': 'curl/7.88.1'})
with urllib.request.urlopen(req, context=ctx) as r:
    soup = BeautifulSoup(r.read(), 'html.parser')
    entry = soup.find('div', class_='entry-content')
    web_text = entry.get_text() if entry else ""

conn = sqlite3.connect('data/duohub.db')
c = conn.cursor()
c.execute("SELECT title, content, audio_url FROM readings WHERE source LIKE '%level1/chapter2%'")
row = c.fetchone()

print('=== DB TITLE ===')
print(row[0] if row else "None")
print('\n=== DB AUDIO ===')
print(row[2] if row else "None")
print('\n=== DB TEXT (first 400 chars) ===')
print(row[1][:400] if row else "None")
print('\n=== WEB TEXT (first 400 chars) ===')
print(web_text[:400])
