import sqlite3

# Diccionario exhaustivo con las correcciones completas y naturales
UPDATES = {
    # Casos especiales de columnas desplazadas o palabras cortadas
    546: {
        'word': 'Take care',
        'translation': 'Cuídate',
        'example_en': 'Have a nice day! Take care and catch you later!',
        'example_es': '¡Que tengas un buen día! ¡Cuídate y nos vemos luego!'
    },
    597: {
        'word': 'Partner',
        'translation': 'Pareja (formal o informal)',
        'example_en': 'My partner and I have lived together for three years.',
        'example_es': 'Mi pareja y yo hemos vivido juntos durante tres años.'
    },
    1077: {
        'word': 'Eco-friendly trends',
        'translation': 'Tendencias ecológicas',
        'example_en': 'Many brands follow eco-friendly trends to protect the environment.',
        'example_es': 'Muchas marcas siguen tendencias ecológicas para proteger el medio ambiente.'
    },
    1091: {
        'word': 'Binge-watch',
        'translation': 'Ver en maratón (series)',
        'example_en': 'Many people enjoy binge-watching their favorite shows on weekends.',
        'example_es': 'Muchas personas disfrutan de ver en maratón sus series favoritas los fines de semana.'
    },
    1094: {
        'word': 'Award-winning documentary',
        'translation': 'Documental galardonado',
        'example_en': 'This is an award-winning documentary about climate change.',
        'example_es': 'Este es un documental galardonado sobre el cambio climático.'
    },
    1268: {
        'word': 'Better late than never',
        'translation': 'Más vale tarde que nunca',
        'example_en': 'You finally arrived! Well, better late than never.',
        'example_es': '¡Finalmente llegaste! Bueno, más vale tarde que nunca.'
    },

    # Frases de ejemplo en español truncadas restauradas con texto completo y natural:
    867: {
        'example_es': 'Me llevo muy bien con mis compañeros de trabajo.'
    },
    873: {
        'example_es': 'El salario mínimo aumentará el próximo año.'
    },
    881: {
        'example_es': 'Estoy trabajando medio tiempo en una librería.'
    },
    885: {
        'example_es': 'Trabajo en el turno de noche en el hospital.'
    },
    886: {
        'example_es': 'Nuestro equipo ganó la competencia del proyecto.'
    },
    891: {
        'example_es': 'Él faltó al trabajo debido a una enfermedad.'
    },
    897: {
        'example_es': 'La gripe se está propagando rápidamente este invierno.'
    },
    899: {
        'example_es': 'No puedo dejar de toser debido a este resfriado.'
    },
    905: {
        'example_es': 'Una buena nutrición es crucial para la salud en general.'
    },
    915: {
        'example_es': 'Tomará algunas semanas para una recuperación completa.'
    },
    916: {
        'example_es': 'La higiene personal es esencial para la salud.'
    },
    922: {
        'example_es': 'Reviso mis correos electrónicos en mi teléfono inteligente.'
    },
    931: {
        'example_es': 'Ella hizo una publicación sobre sus vacaciones.'
    },
    932: {
        'example_es': 'Desplazo mi feed para ver qué hay de nuevo.'
    },
    933: {
        'example_es': 'Me gustó tu publicación sobre el concierto.'
    },
    941: {
        'example_es': 'Te enviaré un correo electrónico con los detalles.'
    },
    948: {
        'example_es': 'Ella escribe un blog sobre experiencias de viaje.'
    },
    949: {
        'example_es': 'Usé un motor de búsqueda para encontrar la respuesta.'
    },
    950: {
        'example_es': 'Haz clic en el enlace para acceder al documento.'
    },
    951: {
        'example_es': 'Asegúrate de que tu contraseña sea segura.'
    },
    963: {
        'example_es': 'Lo conocí a través de un conocido en el trabajo.'
    },
    973: {
        'example_es': 'Es alguien en quien puedes confiar para cualquier cosa.'
    },
    983: {
        'example_es': 'Tengo dos hermanos, ambos mayores que yo.'
    },
    987: {
        'example_es': 'Estamos planeando un encuentro social en el parque.'
    },
    988: {
        'example_es': 'La celebración de su cumpleaños fue increíble.'
    },
    994: {
        'example_es': 'Ella sintió tristeza después de escuchar la noticia.'
    },
    997: {
        'example_es': 'El transporte público es ampliamente utilizado en las grandes ciudades.'
    },
    998: {
        'example_es': 'Ella compró un nuevo vehículo la semana pasada.'
    },
    999: {
        'example_es': 'El tráfico en la mañana siempre es pesado.'
    },
    1000: {
        'example_es': 'Su viaje diario al trabajo dura aproximadamente una hora.'
    },
    1001: {
        'example_es': 'Los pasajeros abordaron el avión a tiempo.'
    },
    1005: {
        'example_es': 'Compró una nueva motocicleta el verano pasado.'
    },
    1011: {
        'example_es': 'El límite de velocidad en esta carretera es de 80 km/h.'
    },
    1017: {
        'example_es': 'Uso un pase mensual para el transporte público.'
    },
    1022: {
        'example_es': 'Esta serie de televisión tiene diez temporadas.'
    },
    1024: { # CASO SOUNDTRACK DEL REPORTE DEL USUARIO
        'example_es': 'La banda sonora de esta película es increíble.'
    },
    1029: {
        'example_es': 'Vamos a un concierto de rock la próxima semana.'
    },
    1032: {
        'example_es': 'El estribillo de esta canción es muy pegadizo.'
    },
    1033: {
        'example_es': 'Esa canción exitosa se escucha en todas partes.'
    },
    1034: {
        'example_es': 'Acabo de terminar de leer un libro fantástico.'
    },
    1047: {
        'example_es': 'La ciudad organiza un festival de cine cada verano.'
    },
    1050: {
        'example_es': 'El flamenco es un baile tradicional de España.'
    },
    1051: {
        'example_es': 'El espectáculo de fuegos artificiales fue espectacular.'
    },
    1079: {
        'example_es': 'El video se convirtió en contenido viral de la noche a la mañana.'
    },
    1105: {
        'example_es': 'Nuestra ganancia aumentó un 15% este año.'
    },
    1109: {
        'example_es': 'Los bancos han reducido las tasas de interés este año.'
    },
    1112: {
        'example_es': 'Su mercado objetivo son los jóvenes profesionales.'
    },
    1118: {
        'example_es': 'El trabajo en equipo efectivo mejora la productividad.'
    },
    1119: {
        'example_es': 'La creación de redes de contactos es clave para el éxito empresarial.'
    },
    1122: {
        'example_es': 'Las empresas compiten en un mercado global.'
    },
    1123: {
        'example_es': 'La inflación alta afecta el poder adquisitivo.'
    },
    1141: {
        'example_es': 'Los implantes biónicos ayudan a restaurar funciones perdidas.'
    },
    1154: {
        'example_es': 'El cerebro controla todas las funciones del cuerpo.'
    },
    1158: {
        'example_es': 'Los riñones filtran los desechos de la sangre.'
    },
    1160: {
        'example_es': 'Las vacunas protegen contra enfermedades.'
    },
    1169: {
        'example_es': 'Un terapeuta puede ayudar con problemas emocionales.'
    },
    1173: {
        'example_es': 'Una dieta saludable previene muchas enfermedades.'
    },
    1174: {
        'example_es': 'Una buena higiene del sueño te ayuda a descansar mejor.'
    },
    1177: {
        'example_es': 'Abrí una nueva cuenta bancaria la semana pasada.'
    },
    1178: {
        'example_es': 'Solicitó un préstamo para comprar una casa.'
    },
    1179: {
        'example_es': 'Está tratando de pagar su deuda estudiantil.'
    },
    1184: {
        'example_es': 'El libro está protegido por leyes de derechos de autor.'
    },
    1185: {
        'example_es': 'Ella presentó una demanda contra la empresa.'
    },
    1187: {
        'example_es': 'El jurado llegó a un veredicto de culpabilidad.'
    },
    1190: {
        'example_es': 'La ley laboral protege los derechos de los trabajadores.'
    },
    1197: {
        'example_es': 'La dictadura restringe las libertades de los ciudadanos.'
    },
    1215: {
        'example_es': 'Solicitó la ciudadanía estadounidense el año pasado.'
    },
    1221: {
        'example_es': 'El cambio climático es una preocupación global.'
    },
    1223: {
        'example_es': 'Ella está involucrada en el activismo ambiental.'
    },
    1226: {
        'example_es': 'Las dos naciones firmaron un tratado de paz.'
    },
    1266: {
        'example_es': 'Si sigo gastando así, me quedaré sin dinero.'
    },
    1269: {
        'example_es': 'Leí un libro para pasar el rato mientras esperaba.'
    },
    1270: {
        'example_es': 'Pongámonos en marcha antes de que el tráfico empeore.'
    },
    1278: {
        'example_es': 'Necesito hacer mis deberes antes de la cena.'
    },
    1282: {
        'example_es': 'Los estudiantes tomaron apuntes durante la clase.'
    },
    1283: {
        'example_es': 'A veces tienes que tomar riesgos en la vida.'
    },
    1285: {
        'example_es': 'Finalmente consiguió un trabajo en una gran empresa.'
    },
    1290: {
        'example_es': 'Necesito una taza de café fuerte para despertar.'
    },
    1291: {
        'example_es': 'Estaba en un sueño profundo cuando llamé.'
    },
    1295: {
        'example_es': 'El buen espíritu de equipo es importante en los deportes.'
    },
    1296: {
        'example_es': 'La gestión del tiempo es esencial en los exámenes.'
    },
    1301: {
        'example_es': 'Ella dio una presentación sobre el cambio climático.'
    },
    1303: {
        'example_es': 'Debemos cumplir el plazo para este proyecto.'
    },
    1304: {
        'example_es': 'Las prácticas ayudan a los estudiantes a adquirir experiencia.'
    },
    1317: {
        'example_es': '¿Puedes cuidar a mi perro mientras estoy fuera?'
    }
}

def apply_fixes():
    conn = sqlite3.connect('data/duohub.db')
    cur = conn.cursor()

    count = 0
    for rid, data in UPDATES.items():
        if 'word' in data:
            cur.execute('''
                UPDATE vocabulary
                SET word = ?, translation = ?, example_en = ?, example_es = ?
                WHERE id = ?
            ''', (data['word'], data['translation'], data['example_en'], data['example_es'], rid))
        elif 'translation' in data:
            cur.execute('''
                UPDATE vocabulary
                SET translation = ?, example_es = ?
                WHERE id = ?
            ''', (data['translation'], data['example_es'], rid))
        else:
            cur.execute('''
                UPDATE vocabulary
                SET example_es = ?
                WHERE id = ?
            ''', (data['example_es'], rid))
        count += 1

    conn.commit()
    conn.close()
    print(f"Successfully updated {count} rows in data/duohub.db.")

if __name__ == '__main__':
    apply_fixes()
