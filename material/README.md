# Carpeta de Material y Libros (PDF)

Coloca aquí los archivos PDF de tus libros de inglés para procesarlos automáticamente:

### Archivos sugeridos:
1. **1000 palabras más usadas en inglés** (ej. `1000_palabras.pdf`)
2. **Domina la gramática inglesa** (ej. `gramatica_inglesa.pdf`)
3. **Workbook de inglés completo**

---

### Cómo importar el vocabulario del PDF a la base de datos:
Una vez que hayas copiado el PDF a esta carpeta, abre una terminal en la carpeta `05-english-duo-hub` y ejecuta:

```bash
python scripts/extract_pdf_words.py
```

El script leerá el PDF, detectará las palabras y traducciones, y las asignará en bloques de 5 palabras por día en la plataforma a partir del último día registrado.
