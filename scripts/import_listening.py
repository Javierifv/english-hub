import asyncio
import edge_tts
import json
import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "material", "listening")

os.makedirs(DOCS_PATH, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

LESSONS = [
    # --- LEVEL A1 (Para Javier - Principiante / Básico) ---
    {
        "id_code": "a1_01_request_from_your_boss",
        "day_number": 1,
        "level": "A1",
        "target_user": "Javier (Principiante)",
        "title": "A Request from Your Boss",
        "topic": "Workplace Requests & Priority Management",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/a-request-from-your-boss",
        "audio_filename": "a1_request_from_your_boss.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi, Mario. Can you help me prepare some things for the next month?"),
            ("en-GB-RyanNeural", "OK, sure. What can I help you with?"),
            ("en-GB-SoniaNeural", "I need to visit the customer in Germany. It's important."),
            ("en-GB-RyanNeural", "What can I do to help?"),
            ("en-GB-SoniaNeural", "Can you send an email to the customer? Ask them when I can visit them next week. Please do this first. It's a priority and very urgent."),
            ("en-GB-RyanNeural", "Right. I'll do it today."),
            ("en-GB-SoniaNeural", "Thanks. This next task is also important. Can you invite everyone to the next team meeting?"),
            ("en-GB-RyanNeural", "Yes, I will."),
            ("en-GB-SoniaNeural", "But first you need to book a meeting room. After that, please send everyone an email about it."),
            ("en-GB-RyanNeural", "Yes, of course."),
            ("en-GB-SoniaNeural", "And finally, can you write a short report about our new project? I have to give a presentation to our managers next month. Please do it when you have time – sometime in the next two or three weeks. It's not too urgent."),
            ("en-GB-RyanNeural", "Sure, no problem. I can do it this week."),
            ("en-GB-SoniaNeural", "There's no hurry. Take your time.")
        ],
        "chunks": [
            "Hi Mario. Can you help me prepare some things for the next month?",
            "I need to visit the customer in Germany. It's important.",
            "Can you send an email to the customer? Ask them when I can visit them next week.",
            "Please do this first. It's a priority and very urgent.",
            "Can you invite everyone to the next team meeting?",
            "But first you need to book a meeting room.",
            "And finally, can you write a short report about our new project?",
            "There's no hurry. Take your time."
        ]
    },
    {
        "id_code": "a1_02_booking_a_table",
        "day_number": 2,
        "level": "A1",
        "target_user": "Javier (Principiante)",
        "title": "Booking a Table at a Restaurant",
        "topic": "Restaurant Reservation & Confirmation",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/booking-table",
        "audio_filename": "a1_booking_a_table.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good evening, Mario's Restaurant. How can I help you?"),
            ("en-GB-RyanNeural", "Hello, I would like to book a table for dinner, please."),
            ("en-GB-SoniaNeural", "Of course. For what day and what time?"),
            ("en-GB-RyanNeural", "For tomorrow night, Wednesday, at seven thirty."),
            ("en-GB-SoniaNeural", "And for how many people?"),
            ("en-GB-RyanNeural", "A table for four people, please."),
            ("en-GB-SoniaNeural", "Inside or outside on the terrace?"),
            ("en-GB-RyanNeural", "Outside on the terrace, please, if possible."),
            ("en-GB-SoniaNeural", "Wonderful. Can I take your name and contact phone number?"),
            ("en-GB-RyanNeural", "Yes, my name is David Miller, and my number is 555-0192."),
            ("en-GB-SoniaNeural", "Great. Table for four, Wednesday at seven thirty. We look forward to seeing you tomorrow, Mr. Miller."),
            ("en-GB-RyanNeural", "Thank you very much. Goodbye.")
        ],
        "chunks": [
            "Good evening, Mario's Restaurant. How can I help you?",
            "Hello, I would like to book a table for dinner, please.",
            "For tomorrow night, Wednesday, at seven thirty.",
            "A table for four people, please.",
            "Outside on the terrace, please, if possible.",
            "Can I take your name and contact phone number?",
            "We look forward to seeing you tomorrow, Mr. Miller."
        ]
    },
    {
        "id_code": "a1_03_the_first_english_class",
        "day_number": 3,
        "level": "A1",
        "target_user": "Javier (Principiante)",
        "title": "The First English Class",
        "topic": "Classroom Welcome, Rules & Schedule",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/the-first-english-class",
        "audio_filename": "a1_the_first_english_class.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning everyone, and welcome to our English class."),
            ("en-GB-SoniaNeural", "My name is Ms. Jenkins, and I am your teacher for this term."),
            ("en-GB-SoniaNeural", "Before we begin, here are three important rules for our course."),
            ("en-GB-SoniaNeural", "First, please arrive on time. Our class starts at nine o'clock sharp every morning."),
            ("en-GB-SoniaNeural", "Second, please speak in English as much as you can, even when you make mistakes. Making mistakes is part of learning."),
            ("en-GB-SoniaNeural", "Third, bring your notebook, a pen, and an English dictionary every day."),
            ("en-GB-SoniaNeural", "Our homework will be posted on the board every Thursday."),
            ("en-GB-SoniaNeural", "Does anyone have any questions? Great, let's open our books to page five.")
        ],
        "chunks": [
            "Good morning everyone, and welcome to our English class.",
            "My name is Ms. Jenkins, and I am your teacher for this term.",
            "First, please arrive on time. Our class starts at nine o'clock sharp.",
            "Second, please speak in English as much as you can.",
            "Making mistakes is part of learning.",
            "Third, bring your notebook, a pen, and an English dictionary.",
            "Let's open our books to page five."
        ]
    },
    {
        "id_code": "a1_04_organising_a_group_project",
        "day_number": 4,
        "level": "A1",
        "target_user": "Javier (Principiante)",
        "title": "Organising a Group Project",
        "topic": "Student Collaboration & Task Division",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/organising-group-project",
        "audio_filename": "a1_organising_a_group_project.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi Lucas, we need to organise our project for Friday."),
            ("en-GB-RyanNeural", "Yes, Clara. We have ten minutes for the presentation."),
            ("en-GB-SoniaNeural", "Exactly. Let's divide the slides. Who wants to do the introduction?"),
            ("en-GB-RyanNeural", "I can do the introduction and explain the background."),
            ("en-GB-SoniaNeural", "Perfect. Then I will present the data and research results."),
            ("en-GB-RyanNeural", "Good idea. What about the conclusion and questions?"),
            ("en-GB-SoniaNeural", "We can both answer the questions from the audience at the end."),
            ("en-GB-RyanNeural", "Agreed. Let's meet tomorrow at two in the library to practice together."),
            ("en-GB-SoniaNeural", "Sounds like a plan. See you tomorrow.")
        ],
        "chunks": [
            "Hi Lucas, we need to organise our project for Friday.",
            "We have ten minutes for the presentation.",
            "Let's divide the slides. Who wants to do the introduction?",
            "I can do the introduction and explain the background.",
            "Then I will present the data and research results.",
            "Let's meet tomorrow at two in the library to practice together."
        ]
    },
    {
        "id_code": "a1_05_a_voicemail_message",
        "day_number": 5,
        "level": "A1",
        "target_user": "Javier (Principiante)",
        "title": "A Voicemail Message",
        "topic": "Office Voicemail, Order Confirmation & Callback",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/voicemail-message",
        "audio_filename": "a1_a_voicemail_message.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, this is a message for Mr. Javier Flores."),
            ("en-GB-SoniaNeural", "My name is Sarah Jenkins from Metro Logistics."),
            ("en-GB-SoniaNeural", "I am calling regarding your delivery order number 4082."),
            ("en-GB-SoniaNeural", "We need to confirm your delivery address before shipping the package tomorrow morning."),
            ("en-GB-SoniaNeural", "Please call us back at 555-0144 when you get this message."),
            ("en-GB-SoniaNeural", "Our office is open today until six in the evening."),
            ("en-GB-SoniaNeural", "If you call after six, you can leave another message with your confirmation."),
            ("en-GB-SoniaNeural", "Thank you, and have a pleasant day.")
        ],
        "chunks": [
            "Hello, this is a message for Mr. Javier Flores.",
            "My name is Sarah Jenkins from Metro Logistics.",
            "I am calling regarding your delivery order number 4082.",
            "We need to confirm your delivery address before shipping the package.",
            "Please call us back at 555-0144 when you get this message.",
            "Our office is open today until six in the evening."
        ]
    },

    # --- LEVEL A2 (Para Compañero - Pre-intermedio) ---
    {
        "id_code": "a2_01_morning_briefing",
        "day_number": 6,
        "level": "A2",
        "target_user": "Compañero (Pre-intermedio)",
        "title": "A Morning Briefing at Work",
        "topic": "Operations Kickoff, Priorities & Safety Standards",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/morning-briefing",
        "audio_filename": "a2_morning_briefing.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Morning team. Let's do a quick five-minute briefing before we kick off today's shift."),
            ("en-GB-RyanNeural", "We have three main operational priorities today."),
            ("en-GB-RyanNeural", "First, container shipment forty-two arrived early at the loading dock, so we need two teams to inspect and unload by eleven o'clock."),
            ("en-GB-RyanNeural", "Second, the safety audit is scheduled for two this afternoon. Please double-check that all emergency exits are clear and personal protective equipment is worn at all times."),
            ("en-GB-RyanNeural", "Lastly, if anyone notices any delay in the inventory software, report it immediately to technical support so we avoid shipping bottlenecks."),
            ("en-GB-RyanNeural", "Any questions? Alright, let's have a productive and safe day.")
        ],
        "chunks": [
            "Morning team. Let's do a quick five-minute briefing before we kick off today's shift.",
            "We have three main operational priorities today.",
            "Container shipment forty-two arrived early at the loading dock.",
            "The safety audit is scheduled for two this afternoon.",
            "Please double-check that all emergency exits are clear.",
            "Report any delay immediately to technical support so we avoid shipping bottlenecks."
        ]
    },
    {
        "id_code": "a2_02_free_time_sports_centre",
        "day_number": 7,
        "level": "A2",
        "target_user": "Compañero (Pre-intermedio)",
        "title": "Free Time & Sports Centre Activities",
        "topic": "Calling Reception, Membership, Schedule & Fees",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/free-time",
        "audio_filename": "a2_free_time_sports_centre.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, Riverside Leisure Centre. How can I help you today?"),
            ("en-GB-RyanNeural", "Hi, I'm calling to find out about your adult swimming classes and gym facilities."),
            ("en-GB-SoniaNeural", "Certainly. Our heated swimming pool is open from six in the morning until nine at night. We have lane swimming every weekday morning, and beginner technique classes on Tuesdays and Thursdays at seven in the evening."),
            ("en-GB-RyanNeural", "That sounds ideal. How much does a monthly pass cost?"),
            ("en-GB-SoniaNeural", "A standard monthly pass including pool and gym access is forty-five pounds. If you join as a pair with a friend, we currently offer a ten percent discount for both members."),
            ("en-GB-RyanNeural", "That is great value. Can I register online or do I need to visit in person?"),
            ("en-GB-SoniaNeural", "You can easily register directly on our website, or drop by with your ID card anytime this afternoon."),
            ("en-GB-RyanNeural", "Excellent, thank you for your help.")
        ],
        "chunks": [
            "Hello, Riverside Leisure Centre. How can I help you today?",
            "I'm calling to find out about your adult swimming classes and gym facilities.",
            "Our heated swimming pool is open from six in the morning until nine at night.",
            "We have lane swimming every weekday morning, and beginner classes on Tuesdays.",
            "If you join as a pair with a friend, we offer a ten percent discount.",
            "You can easily register directly on our website."
        ]
    },
    {
        "id_code": "a2_03_changing_meeting_plans",
        "day_number": 8,
        "level": "A2",
        "target_user": "Compañero (Pre-intermedio)",
        "title": "Changing Meeting Plans",
        "topic": "Phone Coordination, Transport Delay & Rescheduling",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/changing-plans",
        "audio_filename": "a2_changing_meeting_plans.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, Amanda speaking."),
            ("en-GB-RyanNeural", "Hi Amanda, it's Daniel. I'm afraid I have a bit of a problem regarding our meeting this afternoon."),
            ("en-GB-SoniaNeural", "Oh, is everything alright?"),
            ("en-GB-RyanNeural", "Yes, but my train has been delayed by almost an hour due to signal problems outside the city. I won't be able to make it to your office by two o'clock."),
            ("en-GB-SoniaNeural", "Don't worry at all. Would you prefer to push it back to four o'clock, or would tomorrow morning work better for you?"),
            ("en-GB-RyanNeural", "Four o'clock today would be fantastic if your schedule allows it. I should definitely arrive by three thirty."),
            ("en-GB-SoniaNeural", "Four o'clock is completely fine. I'll update the calendar invitation right away and send you the new link."),
            ("en-GB-RyanNeural", "Thanks so much for your understanding, Amanda. See you at four.")
        ],
        "chunks": [
            "I'm afraid I have a bit of a problem regarding our meeting this afternoon.",
            "My train has been delayed by almost an hour due to signal problems.",
            "I won't be able to make it to your office by two o'clock.",
            "Would you prefer to push it back to four o'clock, or would tomorrow work better?",
            "Four o'clock today would be fantastic if your schedule allows it.",
            "I'll update the calendar invitation right away and send you the new link."
        ]
    },
    {
        "id_code": "a2_04_facts_and_figures",
        "day_number": 9,
        "level": "A2",
        "target_user": "Compañero (Pre-intermedio)",
        "title": "Facts & Figures: Quarterly Report",
        "topic": "Data Presentation, Growth Metrics & Consistency",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/facts-and-figures",
        "audio_filename": "a2_facts_and_figures.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning, ladies and gentlemen. Today I would like to present the key performance metrics of our learning program over the past quarter."),
            ("en-GB-SoniaNeural", "As you can see on the screen, active daily participation increased by thirty-four percent compared to last year."),
            ("en-GB-SoniaNeural", "More importantly, eighty-two percent of our participants completed their daily targets of fifteen minutes of reading and five minutes of speaking without breaking their streaks."),
            ("en-GB-SoniaNeural", "We also observed a forty percent reduction in comprehension errors during weekly check-ins."),
            ("en-GB-SoniaNeural", "In conclusion, consistent daily practice in pairs has proven to be twice as effective as occasional long study sessions. Thank you for your attention, and now I'd be glad to take any questions.")
        ],
        "chunks": [
            "Today I would like to present the key performance metrics of our learning program.",
            "Active daily participation increased by thirty-four percent compared to last year.",
            "Eighty-two percent of participants completed their daily targets without breaking their streaks.",
            "We also observed a forty percent reduction in comprehension errors.",
            "Consistent daily practice in pairs has proven to be twice as effective."
        ]
    },
    {
        "id_code": "a2_05_giving_directions_in_town",
        "day_number": 10,
        "level": "A2",
        "target_user": "Compañero (Pre-intermedio)",
        "title": "Giving Directions in Town",
        "topic": "Street Navigation, Landmarks & Finding Central Station",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/giving-directions",
        "audio_filename": "a2_giving_directions_in_town.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Excuse me, could you help me? I'm trying to find the central train station, but I think I am turned around."),
            ("en-GB-SoniaNeural", "No problem at all, it's quite close. Go straight along this avenue for two blocks until you see the cathedral on your left."),
            ("en-GB-RyanNeural", "Straight ahead past the cathedral, okay."),
            ("en-GB-SoniaNeural", "Exactly. At the traffic lights right after the cathedral, turn right onto Victoria Street. Keep walking for about three minutes, pass the public library, and you'll see the main entrance of the station right across the square."),
            ("en-GB-RyanNeural", "Turn right after the cathedral, pass the library, and it's on the square. How long does the walk take?"),
            ("en-GB-SoniaNeural", "It's only about an eight-minute walk from here."),
            ("en-GB-RyanNeural", "Wonderful. Thank you so much for your help!"),
            ("en-GB-SoniaNeural", "You're welcome! Have a safe journey.")
        ],
        "chunks": [
            "I'm trying to find the central train station, but I think I am turned around.",
            "Go straight along this avenue for two blocks until you see the cathedral.",
            "At the traffic lights right after the cathedral, turn right onto Victoria Street.",
            "Keep walking for about three minutes, pass the public library.",
            "You'll see the main entrance of the station right across the square.",
            "It's only about an eight-minute walk from here."
        ]
    }
]

async def generate_lesson_audio(lesson):
    out_path = os.path.join(AUDIO_DIR, lesson["audio_filename"])
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"Audio file already exists for {lesson['title']}: {out_path}")
        return
        
    print(f"Generating audio for {lesson['title']} ({lesson['level']})...")
    with open(out_path, "wb") as f_out:
        for voice, text in lesson["dialogue"]:
            communicate = edge_tts.Communicate(text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f_out.write(chunk["data"])
    print(f"  -> Generated {out_path} ({os.path.getsize(out_path)} bytes)")

async def main():
    print("=== Generating Audio Files with Edge Neural Voices ===")
    for l in LESSONS:
        await generate_lesson_audio(l)
        
    print("\n=== Updating Database: listening_shadowing ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if level column exists
    cur.execute("PRAGMA table_info(listening_shadowing)")
    cols = [col[1] for col in cur.fetchall()]
    if 'audio_filename' not in cols:
        print("Adding audio_filename column to listening_shadowing...")
        cur.execute("ALTER TABLE listening_shadowing ADD COLUMN audio_filename TEXT")
        conn.commit()
    if 'source' not in cols:
        print("Adding source column to listening_shadowing...")
        cur.execute("ALTER TABLE listening_shadowing ADD COLUMN source TEXT")
        conn.commit()

    # Clear existing listening_shadowing to replace with structured curriculum
    cur.execute("DELETE FROM listening_shadowing")
    conn.commit()
    
    for l in LESSONS:
        # Full transcript text formatted
        full_transcript = " ".join([text for _, text in l["dialogue"]])
        
        # Audio URL serves locally via Flask /audio/<filename>
        audio_url = f"/audio/{l['audio_filename']}"
        
        # Rough duration calculation: ~150 words per minute
        word_count = len(full_transcript.split())
        est_duration = max(25, round(word_count / 2.5))
        
        cur.execute("""
        INSERT INTO listening_shadowing (day_number, title, level, audio_url, transcript, duration_seconds, shadowing_chunks, audio_filename, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            l["day_number"],
            l["title"],
            l["level"],
            audio_url,
            full_transcript,
            est_duration,
            json.dumps(l["chunks"]),
            l["audio_filename"],
            l["source"]
        ))
        
    conn.commit()
    conn.close()
    print("Database updated with 10 structured A1 & A2 listening clips!")
    
    # Generate docs/LISTENING_TRAZABILIDAD.md
    md_path = os.path.join(DOCS_PATH, "LISTENING_TRAZABILIDAD.md")
    print(f"Generating traceability documentation at {md_path}...")
    
    md_content = f"""# 🎧 Matriz de Trazabilidad: Audios & Listening (DuoHub)
**Fecha de Generación:** 2026-10-06  
**Fuentes Principales:** [British Council LearnEnglish A1 & A2](https://learnenglish.britishcouncil.org/) & Robinson Crusoe In Levels  
**Motor de Generación Acústica:** Microsoft Edge Neural Voices (HD Studio Audio: `en-GB-SoniaNeural`, `en-GB-RyanNeural`)  
**Total de Pistas en Curriculum:** {len(LESSONS)} audios interactivos  

---

## 🎯 Distribución por Marco Común Europeo (MCER / CEFR)

| Nivel CEFR | Perfil Asignado | Enfoque Pedagógico | Pistas Disponibles | Voces Empleadas |
| :--- | :--- | :--- | :--- | :--- |
| **A1 (Básico / Principiante)** | **Javier** | Oraciones cortas, ritmo pausado, situaciones de oficina y vida diaria esenciales. | {sum(1 for l in LESSONS if l['level'] == 'A1')} pistas (1 al 5) | Sonia (Manager/Host) & Ryan (Assistant/Guest) |
| **A2 (Pre-Intermedio)** | **Compañero** | Diálogos con vocabulario operativo, coordinación de turnos, reuniones y direcciones. | {sum(1 for l in LESSONS if l['level'] == 'A2')} pistas (6 al 10) | Ryan (Lead) & Sonia (Professional) |

> [!NOTE]
> **Autonomía de Aprendizaje:**  
> - **Javier** puede escuchar y transcribir el bloque **A1** (empezando con *A Request from Your Boss*) sin la frustración de la velocidad de A2.  
> - El **compañero** puede ingresar y seleccionar directamente el bloque **A2** para mantener su desafío individual.  
> - Cada usuario tiene su propio selector de nivel en la interfaz.

---

## 📑 Inventario Detallado de Audios & Transcripciones Canónicas

"""
    for idx, l in enumerate(LESSONS, 1):
        dialogue_text = "\n".join([f"> **{v.split('-')[2].replace('Neural', '')}:** {t}" for v, t in l["dialogue"]])
        md_content += f"""### {idx}. [{l['level']}] {l['title']}
- **Destinatario Principal:** {l['target_user']}
- **Tema / Contexto:** {l['topic']}
- **Archivo Local:** [`material/listening/{l['audio_filename']}`](file:///c:/Users/flore/dev/proyectos_personales/05-english-duo-hub/material/listening/{l['audio_filename']})
- **Ruta Web en App:** `/audio/{l['audio_filename']}`
- **Fuente Oficial:** [{l['source']}]({l['source']})
- **Fragmentos para Shadowing:** {len(l['chunks'])} frases dosificadas

#### 📜 Transcripción Canónica:
{dialogue_text}

---
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Traceability documentation created successfully at {md_path}!")

if __name__ == "__main__":
    asyncio.run(main())
