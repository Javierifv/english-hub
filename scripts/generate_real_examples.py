import os
import json
import sqlite3
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "duohub.db")
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 1. Read API key
api_key = ""
with open(ENV_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY="):
            api_key = line.strip().split("=")[1]
            break

if not api_key:
    raise ValueError("GEMINI_API_KEY no encontrada en .env")

model = "gemini-3.5-flash"
api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 2. Get words with placeholder examples
cursor.execute("""
    SELECT id, word, translation, part_of_speech, category
    FROM vocabulary
    WHERE example_en LIKE '%Practice sentence%'
       OR example_es LIKE '%Oraci%'
       OR example_en IS NULL
       OR example_es IS NULL
       OR example_en = ''
       OR example_es = ''
    ORDER BY id ASC
""")
rows = cursor.fetchall()
print(f"Total de palabras a procesar: {len(rows)}")

batch_size = 35

def call_gemini_batch(batch):
    items_prompt = []
    for r in batch:
        items_prompt.append({
            "id": r[0],
            "word": r[1],
            "translation": r[2]
        })

    prompt_text = f"""Eres un profesor experto de inglés. Para cada palabra en la lista proporcionada, crea:
1. 'example_en': Una oración cotidiana, clara y natural en inglés (nivel A1-A2) que use la palabra tal como se indica.
2. 'example_es': La traducción natural y precisa al español de esa oración.

IMPORTANTE:
- NO uses frases genéricas como "This is a...", "I like...", o "Practice sentence".
- Usa situaciones reales y comunicativas (conversaciones, compras, viajes, casa, trabajo).
- Devuelve EXACTAMENTE un arreglo JSON con objetos con las claves: "id" (número), "example_en" (texto), "example_es" (texto).

Lista de palabras:
{json.dumps(items_prompt, ensure_ascii=False)}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.3
        }
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(raw_text)

total_updated = 0
for i in range(0, len(rows), batch_size):
    batch = rows[i:i + batch_size]
    batch_num = (i // batch_size) + 1
    total_batches = (len(rows) + batch_size - 1) // batch_size
    print(f"Procesando lote {batch_num}/{total_batches} ({len(batch)} palabras)...")

    success = False
    for attempt in range(3):
        try:
            results = call_gemini_batch(batch)
            if isinstance(results, dict) and "items" in results:
                results = results["items"]
            elif isinstance(results, dict) and "words" in results:
                results = results["words"]

            # Update in DB
            for item in results:
                w_id = item.get("id")
                ex_en = item.get("example_en", "").strip()
                ex_es = item.get("example_es", "").strip()
                if w_id and ex_en and ex_es:
                    cursor.execute("""
                        UPDATE vocabulary
                        SET example_en = ?, example_es = ?
                        WHERE id = ?
                    """, (ex_en, ex_es, w_id))
                    total_updated += 1
            conn.commit()
            success = True
            print(f"  -> Lote {batch_num} guardado exitosamente.")
            break
        except Exception as e:
            print(f"  -> Intento {attempt + 1} falló en lote {batch_num}: {e}")
            time.sleep(2)

    if not success:
        print(f"  [ALERTA] No se pudo procesar el lote {batch_num}")

    time.sleep(1)

conn.close()
print(f"\n¡Proceso finalizado! Total de palabras actualizadas con ejemplos reales: {total_updated}")
