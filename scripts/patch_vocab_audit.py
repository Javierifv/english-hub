import sqlite3

conn = sqlite3.connect('data/duohub.db')
c = conn.cursor()

updates = [
    (600, 'Father-in-law', 'Suegro', None, None),
    (876, 'One-year contract', 'Contrato de un año', None, None),
    (880, 'Full-time', 'Tiempo completo / Jornada completa', None, None),
    (1012, 'One-way ticket', 'Billete de ida', None, None),
    (1013, 'Boarding pass', 'Tarjeta de embarque', 'Please show your boarding pass at the gate.', 'Por favor muestre su tarjeta de embarque en la puerta.'),
    (1014, 'Round-trip ticket', 'Billete de ida y vuelta', None, None),
    (1015, 'Return ticket', 'Billete de regreso', 'I bought a return ticket for Sunday evening.', 'Compré un billete de regreso para el domingo por la tarde.'),
    (1040, 'E-book', 'Libro electrónico', None, None),
    (1053, 'Best regards', 'Atentamente', None, None),
    (1067, 'To make headlines', 'Ser noticia / Salir en los titulares', None, None),
    (1069, 'To manipulate public opinion', 'Manipular la opinión pública', None, None),
    (1072, 'To fact-check information', 'Verificar los datos / la información', None, None),
    (1086, 'A lifestyle trend', 'Una tendencia de estilo de vida', None, None),
    (1087, 'Influencer marketing', 'Marketing de influencers', None, None),
    (1090, 'Binge-watching', 'Ver en maratón (series/películas)', None, None),
    (1172, 'Mental health', 'Salud mental', 'Regular exercise is good for physical and mental health.', 'El ejercicio regular es bueno para la salud física y mental.'),
    (1181, 'Lease agreement', 'Contrato de arrendamiento', None, None),
    (1182, 'Breach of contract', 'Incumplimiento de contrato', None, None),
    (1250, 'Research integrity', 'Integridad en la investigación', None, None),
    (1252, 'State-of-the-art', 'De última generación / Vanguardista', None, None),
    (1261, 'All ears', 'Soy todo oídos / Escuchar con atención', None, None),
    (1272, 'Call the shots', 'Tener el control / Tomar las decisiones', None, None),
    (1278, 'Do homework', 'Hacer los deberes / la tarea', None, None),
    (1280, 'Do someone a favor', 'Hacer un favor a alguien', None, None),
    (1306, 'Get over', 'Superar (un problema o enfermedad)', None, None),
    (1314, 'Bring up', 'Mencionar un tema / Criar a un niño', None, None),
    (1316, 'Bring out', 'Lanzar un producto / Resaltar una cualidad', None, None),
    (1320, 'Look up', 'Buscar información (en libro o internet)', None, None),
    (1325, 'Turn down', 'Rechazar una oferta / Bajar el volumen', None, None),
]

for wid, word, trans, ex_en, ex_es in updates:
    if ex_en and ex_es:
        c.execute("UPDATE vocabulary SET word = ?, translation = ?, example_en = ?, example_es = ? WHERE id = ?", (word, trans, ex_en, ex_es, wid))
    else:
        c.execute("UPDATE vocabulary SET word = ?, translation = ? WHERE id = ?", (word, trans, wid))

conn.commit()
print(f"Successfully patched {len(updates)} vocabulary items in duohub.db!")
conn.close()
