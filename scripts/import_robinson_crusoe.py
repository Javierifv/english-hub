import urllib.request
import json
import ssl
import re
import sqlite3
import os
from html import unescape
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
os.makedirs(DOCS_PATH, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'curl/7.88.1'}

def fetch_all_pages():
    all_pages = []
    for p in [1, 2]:
        url = f'https://www.robinsoncrusoeinlevels.com/wp-json/wp/v2/pages?per_page=100&page={p}'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as res:
            data = json.loads(res.read().decode('utf-8'))
            all_pages.extend(data)
    return all_pages

def clean_html_content(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Remove navigation buttons and promo blocks
    for div in soup.find_all('div', class_=re.compile(r'et_pb_promo|et_pb_button|et_pb_cta')):
        div.decompose()
    for a in soup.find_all('a'):
        if 'Next chapter' in a.get_text() or 'englishinshop' in a.get('href', ''):
            a.decompose()
            
    # Extract audio URLs before stripping
    audio_urls = []
    for a in soup.find_all('a', href=re.compile(r'\.mp3$')):
        audio_urls.append(a['href'])
    for audio in soup.find_all('audio'):
        if audio.get('src'):
            audio_urls.append(audio['src'])
        for src in audio.find_all('source'):
            if src.get('src'):
                audio_urls.append(src['src'])
                
    # Also regex for any remaining mp3 in raw html
    raw_mp3s = re.findall(r'https?://[^\s"\'<>]+\.mp3', raw_html)
    for m in raw_mp3s:
        if m not in audio_urls:
            audio_urls.append(m)

    # Get clean text paragraphs
    paragraphs = []
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        # Filter out audio url lines and junk
        if not text or text.endswith('.mp3') or 'You can buy the whole book' in text:
            continue
        paragraphs.append(text)
        
    cleaned_text = "\n\n".join(paragraphs)
    # If soup didn't catch p tags cleanly:
    if not cleaned_text:
        cleaned_text = soup.get_text()
        
    return cleaned_text, audio_urls

def parse_chapter_number_and_level(slug, link, title):
    # Level: 1 -> A1, 2 -> B1, 3 -> B2
    level_code = "A1"
    level_num = 1
    if "/level2/" in link or "L2" in title:
        level_code = "B1"
        level_num = 2
    elif "/level3/" in link or "L3" in title:
        level_code = "B2"
        level_num = 3
    elif "/level1/" in link or "L1" in title:
        level_code = "A1"
        level_num = 1
        
    # Chapter number
    ch_match = re.search(r'chapter(\d+)', slug.lower())
    if not ch_match:
        ch_match = re.search(r'chapter\s*(\d+)', title.lower())
    ch_num = int(ch_match.group(1)) if ch_match else 0
    return level_num, level_code, ch_num

def main():
    print("Fetching pages from Robinson Crusoe in Levels...")
    pages = fetch_all_pages()
    print(f"Total pages fetched: {len(pages)}")
    
    chapter_pages = []
    for p in pages:
        slug = p.get('slug', '')
        link = p.get('link', '')
        title = unescape(p.get('title', {}).get('rendered', ''))
        
        # Only chapters (e.g. level1/chapter1)
        if re.search(r'chapter\d+', slug) and ('/level1/' in link or '/level2/' in link or '/level3/' in link):
            level_num, level_code, ch_num = parse_chapter_number_and_level(slug, link, title)
            if ch_num > 0:
                chapter_pages.append((level_num, ch_num, level_code, p))
                
    # Sort by level, then chapter number
    chapter_pages.sort(key=lambda x: (x[0], x[1]))
    print(f"Filtered {len(chapter_pages)} Robinson Crusoe chapters.")
    
    # Connect DB and ensure columns
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if audio_url column exists in readings
    cur.execute("PRAGMA table_info(readings)")
    cols = [col[1] for col in cur.fetchall()]
    if 'audio_url' not in cols:
        print("Adding audio_url column to readings table...")
        cur.execute("ALTER TABLE readings ADD COLUMN audio_url TEXT")
        conn.commit()
        
    records = []
    for level_num, ch_num, level_code, p in chapter_pages:
        raw_html = p.get('content', {}).get('rendered', '')
        text, audio_urls = clean_html_content(raw_html)
        audio_url = audio_urls[0] if audio_urls else ""
        
        # Clean title
        title_raw = unescape(p.get('title', {}).get('rendered', ''))
        # Try to find subtitle from first line of text like "CHAPTER 1 – HAT"
        subtitle = ""
        lines = text.split("\n")
        first_line = lines[0].strip() if lines else ""
        if "CHAPTER" in first_line.upper():
            subtitle = first_line
            # remove it from main text so it doesn't duplicate
            text = "\n".join(lines[1:]).strip()
            
        final_title = f"Robinson Crusoe (L{level_num}): Ch. {ch_num} - {subtitle if subtitle else title_raw}"
        word_count = len(text.split())
        source_url = p.get('link', '')
        
        records.append({
            'level_num': level_num,
            'chapter': ch_num,
            'level': level_code,
            'title': final_title,
            'content': text,
            'audio_url': audio_url,
            'source': source_url,
            'words': word_count,
            'topic': 'Robinson Crusoe Classic Literature'
        })

    # Clear existing Robinson Crusoe readings if any, and insert
    cur.execute("DELETE FROM readings WHERE source LIKE '%robinsoncrusoeinlevels.com%'")
    conn.commit()
    
    print(f"Inserting {len(records)} chapters into SQLite database...")
    for i, r in enumerate(records, 1):
        cur.execute("""
        INSERT INTO readings (day_number, title, level, topic, estimated_minutes, content, source, key_vocabulary, audio_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['chapter'],
            r['title'],
            r['level'],
            r['topic'],
            max(10, round(r['words'] / 60)), # reading time based on 60 wpm for learners
            r['content'],
            r['source'],
            json.dumps([]),
            r['audio_url']
        ))
    conn.commit()
    conn.close()
    print("Database update successful!")
    
    # Generate docs/LECTURAS_TRAZABILIDAD.md
    md_path = os.path.join(DOCS_PATH, "LECTURAS_TRAZABILIDAD.md")
    print(f"Writing traceability document to {md_path}...")
    
    l1_count = sum(1 for r in records if r['level_num'] == 1)
    l2_count = sum(1 for r in records if r['level_num'] == 2)
    l3_count = sum(1 for r in records if r['level_num'] == 3)
    
    md_content = f"""# 📚 Matriz de Trazabilidad: Lecturas (Readings DuoHub)
**Fecha de Generación:** 2026-10-06  
**Fuente Principal:** [Robinson Crusoe in Levels](https://www.robinsoncrusoeinlevels.com/)  
**Total de Lecturas Disponibles:** {len(records)} capítulos  

---

## 🎯 Distribución por Marco Común Europeo (MCER / CEFR)

| Nivel CEFR | Nivel Original | Perfil Recomendado | Capítulos | Palabras Promedio | Audio Disponible |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A1 / A2** | Level 1 | Principiante / Básico (**Javier**) | {l1_count} (Cap. 1 al {l1_count}) | ~500 - 800 palabras | ✅ Narración Lenta (MP3 CDN) |
| **B1** | Level 2 | Intermedio (**Compañero**) | {l2_count} (Cap. 1 al {l2_count}) | ~600 - 900 palabras | ✅ Narración Normal (MP3 CDN) |
| **B2** | Level 3 | Intermedio Alto / Avanzado | {l3_count} (Cap. 1 al {l3_count}) | ~700 - 1100 palabras | ✅ Narración Nativa (MP3 CDN) |

> [!TIP]
> **Pauta de Aprendizaje en Pareja:**  
> - **Javier** puede iniciar directamente con el bloque **A1 (Level 1)**, donde el vocabulario está graduado y las oraciones son directas, con narración de ritmo pausado.  
> - El **compañero** puede seleccionar **B1 (Level 2)** o **B2 (Level 3)** de forma totalmente independiente.  
> - La app permite filtrar por nivel con un solo clic.

---

## 📑 Inventario Completo de Capítulos

| # | Nivel CEFR | Cap. | Título | Palabras | Min. Sugeridos | Audio MP3 | Enlace Original |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
"""
    for idx, r in enumerate(records, 1):
        has_audio = f"[Escuchar MP3]({r['audio_url']})" if r['audio_url'] else "N/A"
        md_content += f"| {idx} | **{r['level']}** | {r['chapter']} | {r['title']} | {r['words']} | {max(10, round(r['words'] / 60))} min | {has_audio} | [Ver Web]({r['source']}) |\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Traceability documentation created successfully at {md_path}!")

if __name__ == "__main__":
    main()
