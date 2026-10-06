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

def clean_chapter_content(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Remove promos and buttons
    for div in soup.find_all('div', class_=re.compile(r'et_pb_promo|et_pb_button|et_pb_cta')):
        div.decompose()
        
    audio_urls = re.findall(r'https?://[^\s"\'<>]+\.mp3', raw_html)
    valid_audio = ""
    for a in audio_urls:
        if 'RC-L' in a:
            valid_audio = a
            break
    if not valid_audio and audio_urls:
        valid_audio = audio_urls[0]

    extracted_title = ""
    story_paragraphs = []
    
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        if not text:
            continue
        # Filter metadata headers
        if re.search(r'robinson crusoe in levels is a book', text, re.IGNORECASE):
            continue
        if re.search(r'students can read this book', text, re.IGNORECASE):
            continue
        if re.match(r'^level\s*\d+$', text, re.IGNORECASE):
            continue
        if re.match(r'^chapter\s*\d+$', text, re.IGNORECASE):
            continue
        if text.startswith('http') and text.endswith('.mp3'):
            continue
        if 'buy the whole book' in text.lower() or 'next chapter' in text.lower():
            continue
            
        # Check if it's the chapter title like "CHAPTER 2 – STORM"
        ch_title_match = re.search(r'chapter\s*\d+\s*[–-]\s*([a-zA-Z\s]+)', text, re.IGNORECASE)
        if ch_title_match and not extracted_title:
            extracted_title = ch_title_match.group(1).strip().capitalize()
            continue

        # Remaining paragraph is actual story text
        story_paragraphs.append(text)
        
    clean_text = "\n\n".join(story_paragraphs)
    return clean_text, valid_audio, extracted_title

def parse_chapter_info(slug, link, title):
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
        
    ch_match = re.search(r'chapter(\d+)', slug.lower())
    if not ch_match:
        ch_match = re.search(r'chapter\s*(\d+)', title.lower())
    ch_num = int(ch_match.group(1)) if ch_match else 0
    return level_num, level_code, ch_num

def main():
    print("Fetching fresh pages from Robinson Crusoe in Levels...")
    pages = fetch_all_pages()
    
    valid_chapters = []
    for p in pages:
        slug = p.get('slug', '')
        link = p.get('link', '')
        title = unescape(p.get('title', {}).get('rendered', ''))
        
        # EXCLUDE the dummy page id 2 ("The Little Prince" slug chapter1)
        if p.get('id') == 2 or 'little-prince' in p.get('content', {}).get('rendered', ''):
            continue
            
        if re.search(r'chapter\d+', slug) and ('/level1/' in link or '/level2/' in link or '/level3/' in link):
            level_num, level_code, ch_num = parse_chapter_info(slug, link, title)
            # Level 1 only has chapters >= 2 on the website
            if level_num == 1 and ch_num < 2:
                continue
            if ch_num > 0:
                valid_chapters.append((level_num, ch_num, level_code, p))
                
    valid_chapters.sort(key=lambda x: (x[0], x[1]))
    print(f"Total valid Robinson Crusoe chapters: {len(valid_chapters)}")

    records = []
    for level_num, ch_num, level_code, p in valid_chapters:
        raw_html = p.get('content', {}).get('rendered', '')
        text, audio_url, extracted_sub = clean_chapter_content(raw_html)
        
        level_label = f"Nivel {level_num} ({'A1/A2' if level_num==1 else ('B1' if level_num==2 else 'B2')})"
        sub_title = f" – {extracted_sub}" if extracted_sub else ""
        final_title = f"[{level_label}] Cap. {ch_num}{sub_title}"
        
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
            'topic': 'Robinson Crusoe'
        })

    # Update SQLite database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check audio_url column exists
    cur.execute("PRAGMA table_info(readings)")
    cols = [col[1] for col in cur.fetchall()]
    if 'audio_url' not in cols:
        cur.execute("ALTER TABLE readings ADD COLUMN audio_url TEXT")
        
    cur.execute("DELETE FROM readings")
    conn.commit()

    print(f"Inserting {len(records)} verified Robinson Crusoe chapters into SQLite...")
    for r in records:
        cur.execute("""
        INSERT INTO readings (day_number, title, level, topic, estimated_minutes, content, source, key_vocabulary, audio_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['chapter'],
            r['title'],
            r['level'],
            r['topic'],
            max(10, round(r['words'] / 65)),
            r['content'],
            r['source'],
            json.dumps([]),
            r['audio_url']
        ))
    conn.commit()
    conn.close()
    print("Database readings reloaded successfully!")

    # Generate docs/LECTURAS_TRAZABILIDAD.md
    md_path = os.path.join(DOCS_PATH, "LECTURAS_TRAZABILIDAD.md")
    l1_count = sum(1 for r in records if r['level_num'] == 1)
    l2_count = sum(1 for r in records if r['level_num'] == 2)
    l3_count = sum(1 for r in records if r['level_num'] == 3)

    md_content = f"""# 📚 Matriz de Trazabilidad: Lecturas (Robinson Crusoe in Levels)
**Fecha de Verificación:** 2026-10-06  
**Fuente Principal:** [Robinson Crusoe in Levels](https://www.robinsoncrusoeinlevels.com/)  
**Total de Lecturas Disponibles:** {len(records)} capítulos verificados  

---

## 🎯 Distribución por Marco Común Europeo (MCER / CEFR)

| Nivel CEFR | Nivel Web | Capítulos Disponibles | Rango de Capítulos | Vocabulario & Estilo | Audio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A1 / A2** | Level 1 | {l1_count} capítulos | Cap. 2 al 31 | Oraciones simples en presente/pasado, ritmo pausado | ✅ Narración Lenta (MP3) |
| **B1** | Level 2 | {l2_count} capítulos | Cap. 1 al 31 | Tiempo pasado continuo, oraciones compuestas | ✅ Narración Normal (MP3) |
| **B2** | Level 3 | {l3_count} capítulos | Cap. 1 al 31 | Vocabulario literario ampliado, tiempos perfectos | ✅ Narración Nativa (MP3) |

> [!NOTE]
> **Accesibilidad Universal:**  
> Ambos compañeros tienen acceso a todos los niveles y todos los capítulos en el selector. No hay restricciones artificiales de usuario. Cada uno puede elegir el nivel y capítulo que desee estudiar en cualquier momento.

---

## 📑 Inventario Completo de Capítulos

| # | Nivel CEFR | Cap. | Título | Palabras | Min. Sugeridos | Audio MP3 | Enlace Original |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
"""
    for idx, r in enumerate(records, 1):
        has_audio = f"[Escuchar MP3]({r['audio_url']})" if r['audio_url'] else "N/A"
        md_content += f"| {idx} | **{r['level']}** | {r['chapter']} | {r['title']} | {r['words']} | {max(10, round(r['words'] / 65))} min | {has_audio} | [Ver Web]({r['source']}) |\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Documentation saved at {md_path}!")

if __name__ == "__main__":
    main()
