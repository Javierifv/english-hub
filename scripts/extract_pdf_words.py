"""
Script para extraer palabras de vocabulario desde PDFs en la carpeta material/
e importarlas a la base de datos de DuoHub agrupadas en 5 palabras por día.
"""

import os
import re
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL_DIR = os.path.join(BASE_DIR, "material")
DB_PATH = os.path.join(BASE_DIR, "data", "duohub.db")

def parse_pdf(file_path):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[!] La librería 'pypdf' no está instalada. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
        from pypdf import PdfReader

    print(f"[*] Leyendo archivo PDF: {file_path}")
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    print(f"[*] Total de páginas detectadas: {total_pages}")

    full_text = ""
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n{text}"

    return full_text

def extract_word_entries(text):
    """
    Intenta extraer pares palabra - traducción o listas numeradas comunes de libros de vocabulario.
    Patrones comunes:
    - 1. Word /ipa/ : traducción
    - Word - Traducción
    - Word (verb) : Traducción
    """
    entries = []
    lines = text.split("\n")

    pattern1 = re.compile(r"^\s*(?:\d+[\.\)]\s*)?([a-zA-Z\s'-]{2,25})\s*(?:\[|\/)(.*?)(?:\]|\/)?\s*[-:–—]\s*(.*)$")
    pattern2 = re.compile(r"^\s*(?:\d+[\.\)]\s*)?([a-zA-Z\s'-]{2,25})\s*[-:–—]\s*(.*)$")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3 or len(line) > 140:
            continue

        m1 = pattern1.match(line)
        if m1:
            word = m1.group(1).strip()
            ipa = m1.group(2).strip()
            trans = m1.group(3).strip()
            if word and trans and not any(ch.isdigit() for ch in word):
                entries.append({
                    "word": word.lower(),
                    "ipa": f"/{ipa}/" if ipa else "",
                    "translation": trans
                })
            continue

        m2 = pattern2.match(line)
        if m2:
            word = m2.group(1).strip()
            trans = m2.group(2).strip()
            if word and trans and len(word.split()) <= 3 and not any(ch.isdigit() for ch in word):
                entries.append({
                    "word": word.lower(),
                    "ipa": "",
                    "translation": trans
                })

    return entries

def import_to_db(entries):
    if not entries:
        print("[!] No se encontraron entradas reconocibles con el patrón automático.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get highest day_number currently in db
    cursor.execute("SELECT COALESCE(MAX(day_number), 0) FROM vocabulary")
    last_day = cursor.fetchone()[0]
    next_day = max(last_day + 1, 8)

    print(f"[*] Palabras encontradas: {len(entries)}")
    print(f"[*] Se importarán comenzando desde el Día #{next_day} (5 palabras por día)")

    count = 0
    current_day = next_day
    inserted_words = set()

    for item in entries:
        w = item["word"].lower()
        if w in inserted_words:
            continue
        inserted_words.add(w)

        # Check if word already exists in DB
        cursor.execute("SELECT id FROM vocabulary WHERE LOWER(word) = ?", (w,))
        if cursor.fetchone():
            continue

        cursor.execute("""
            INSERT INTO vocabulary (day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            current_day,
            item["word"],
            item.get("ipa", ""),
            "general",
            item["translation"],
            f"Key vocabulary word: {item['word']}",
            f"Practice sentence with '{item['word']}'.",
            f"Oración de práctica con '{item['word']}'.",
            "imported-pdf"
        ))

        count += 1
        if count % 5 == 0:
            current_day += 1

    conn.commit()
    conn.close()
    print(f"[✓] ¡Éxito! Se importaron {count} palabras nuevas en la base de datos hasta el Día #{current_day}.")

def main():
    print("=" * 60)
    print(" DUOHUB - EXTRACTOR DE VOCABULARIO DESDE LIBROS PDF")
    print("=" * 60)

    pdf_files = [f for f in os.listdir(MATERIAL_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"[!] No se encontraron archivos PDF en: {MATERIAL_DIR}")
        print("[!] Por favor copia tus archivos PDF (ej. 1000 palabras) en esa carpeta y vuelve a ejecutar este script.")
        return

    print("[*] Archivos PDF detectados:")
    for i, file_name in enumerate(pdf_files, start=1):
        print(f"  {i}. {file_name}")

    selected_file = pdf_files[0]
    file_path = os.path.join(MATERIAL_DIR, selected_file)
    text = parse_pdf(file_path)
    entries = extract_word_entries(text)
    import_to_db(entries)

if __name__ == "__main__":
    main()
