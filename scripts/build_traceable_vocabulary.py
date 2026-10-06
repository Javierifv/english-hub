import os
import re
import json
import sqlite3
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "material", "Domina el Vocabulario Inglés - English Path_260514_013310.pdf")
MD_OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "VOCABULARIO_TRAZABILIDAD.md")
DB_PATH = os.path.join(BASE_DIR, "data", "duohub.db")

os.makedirs(os.path.join(BASE_DIR, "docs"), exist_ok=True)

print(f"Leyendo archivo PDF: {PDF_PATH}")
reader = PdfReader(PDF_PATH)
total_pages = len(reader.pages)
print(f"Total de páginas: {total_pages}")

# Regex to detect word - translation
# separators: \u2013 (en-dash), \u2014 (em-dash), \u2192 (arrow), -, :, \x96, \ufffd
sep_pattern = r"(?:[\u2013\u2014\u2192\-\x96\x97]|\uFFFD|:)"
word_line_re = re.compile(rf"^([a-zA-Z\s\',-]{{2,35}})\s*{sep_pattern}\s*(.+)$")

current_chapter = "A1 - Nivel Principiante"
current_section = ""

extracted_entries = []
seen_words = set()

for page_num in range(1, total_pages + 1):
    text = reader.pages[page_num - 1].extract_text()
    if not text:
        continue
    
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # Detect chapter / level
    for line in lines[:5]:
        if "Capítulo 1" in line or "A1" in line:
            current_chapter = "A1 - Principiante"
        elif "Capítulo 2" in line or "A2" in line:
            current_chapter = "A2 - Fundamental"
        elif "Capítulo 3" in line or "B1" in line:
            current_chapter = "B1 - Intermedio"
        elif "Capítulo 4" in line or "B2" in line:
            current_chapter = "B2 - Intermedio Alto"

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        
        # Check section titles
        if re.match(r"^\d+\.\d+\.?\s+", line):
            current_section = line
            idx += 1
            continue

        m = word_line_re.match(line)
        if m:
            raw_en = m.group(1).strip()
            raw_es = m.group(2).strip()

            # Filter out headers or long sentences
            if len(raw_en.split()) <= 4 and not any(ch.isdigit() for ch in raw_en) and len(raw_es) < 100:
                clean_en_lower = raw_en.lower()
                
                # Look ahead for example sentence
                ex_en = ""
                ex_es = ""
                if idx + 1 < len(lines) and not word_line_re.match(lines[idx + 1]):
                    next_line = lines[idx + 1]
                    if len(next_line) > 10 and "(" not in next_line and not next_line.startswith("Capítulo"):
                        ex_en = next_line
                        if idx + 2 < len(lines) and "(" in lines[idx + 2]:
                            ex_es = lines[idx + 2].strip("()")

                excerpt = f"Pág. {page_num}: '{line}'"
                if ex_en:
                    excerpt += f" | Ejemplo: '{ex_en}'"

                if clean_en_lower not in seen_words:
                    seen_words.add(clean_en_lower)
                    extracted_entries.append({
                        "word": raw_en,
                        "translation": raw_es,
                        "example_en": ex_en or f"Practice sentence with '{raw_en}'.",
                        "example_es": ex_es or f"Oración de práctica con '{raw_en}'.",
                        "page": page_num,
                        "level": current_chapter,
                        "section": current_section,
                        "excerpt": excerpt
                    })
        idx += 1

print(f"Total de palabras unicas extraídas con trazabilidad: {len(extracted_entries)}")

# Write to VOCABULARIO_TRAZABILIDAD.md
with open(MD_OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("# 📖 Trazabilidad de Vocabulario — Domina el Vocabulario Inglés\n\n")
    f.write(f"**Fuente:** `material/Domina el Vocabulario Inglés - English Path_260514_013310.pdf`  \n")
    f.write(f"**Total de páginas analizadas:** {total_pages}  \n")
    f.write(f"**Total de palabras extraídas:** {len(extracted_entries)}  \n\n")
    f.write("Cada palabra a continuación contiene su nivel, página de origen del libro, traducción y el extracto exacto del texto para verificación y trazabilidad 100% auditada.\n\n")
    f.write("---\n\n")

    f.write("| # | Palabra (EN) | Traducción (ES) | Nivel | Pág. | Extracto Exacto del Libro |\n")
    f.write("| :-: | :--- | :--- | :---: | :-: | :--- |\n")

    for i, item in enumerate(extracted_entries, start=1):
        clean_excerpt = item['excerpt'].replace("|", "/")
        f.write(f"| {i} | **{item['word']}** | {item['translation']} | `{item['level']}` | Pág. {item['page']} | {clean_excerpt} |\n")

print(f"Documento de trazabilidad generado en: {MD_OUTPUT_PATH}")

# Update DB with clean traceable words
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Clear previous words and rebuild with full traceability
cursor.execute("DELETE FROM vocabulary")

words_per_day = 5
current_day = 1

for i, item in enumerate(extracted_entries, start=1):
    cursor.execute("""
        INSERT INTO vocabulary (day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        current_day,
        item["word"],
        "",
        item["level"],
        item["translation"],
        f"Palabra extraída del libro en la Pág. {item['page']}",
        item["example_en"],
        item["example_es"],
        item["section"] or "vocab-book"
    ))
    if i % words_per_day == 0:
        current_day += 1

conn.commit()
cursor.execute("SELECT COUNT(*), MAX(day_number) FROM vocabulary")
print("Base de datos actualizada:", cursor.fetchone())
conn.close()
