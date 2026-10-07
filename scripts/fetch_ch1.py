import urllib.request, ssl, re
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'curl/7.88.1'}

res = urllib.request.urlopen(urllib.request.Request('https://www.robinsoncrusoeinlevels.com/level1/chapter1/', headers=headers), context=ctx)
html = res.read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')

print("Title tag:", soup.title.string if soup.title else "")
paragraphs = []
for p in soup.find_all('p'):
    t = p.get_text().strip()
    if t and not 'robinson crusoe in levels' in t.lower() and not 'students can read' in t.lower():
        paragraphs.append(t)

print("\n--- Paragraphs ---")
for p in paragraphs:
    print(p)

audio = re.findall(r'https?://[^\s"\'<>]+\.mp3', html)
print("\n--- Audio ---")
print(audio)
