# ⚡ DuoHub — English Mastery & Partner Training System

Sistema integral de entrenamiento diario de inglés diseñado para estudiar en pareja con responsabilidad mutua (*peer accountability*), combinando adquisición de vocabulario de alta frecuencia, lectura inmersiva con auditoría de resúmenes, comprensión auditiva por dictado y práctica muscular de pronunciación (*shadowing*).

---

## 🎯 Los 5 Pilares Diarios

| # | Pilar | Tiempo | Objetivo Pedagógico |
| :-: | :--- | :-: | :--- |
| **1** | **Vocabulario (5 palabras)** | 5 min | Aprender y activar 5 palabras del top 1.000 con fonética (IPA), audio nativo y ejemplos. |
| **2** | **Lectura Inmersiva & Resumen** | 15 min | Leer un artículo nivelado (A2-B2), redactar un resumen en inglés y recibir auditoría de errores gramaticales y naturalidad. |
| **3** | **Deep Listening & Dictado** | 10 min | Escucha activa (técnica *Dictogloss*) con retroceso de 5s y comparador visual (*diff*) contra la transcripción real. |
| **4** | **Shadowing Studio** | 5 min | Repetición muscular simultánea de frases nativas y grabación directa con micrófono para autoevaluación. |
| **5** | **Speaking Challenge** | 5 min | Audio de WhatsApp diario a tu compañero respondiendo a la pregunta del día e integrando las 5 palabras aprendidas. |

---

## 🚀 Inicio Rápido

### En Windows (1 Clic)
Haz doble clic en:
```
iniciar_hub.bat
```
El script creará automáticamente el entorno virtual, instalará las dependencias necesarias (`Flask`, `pypdf`), verificará la base de datos SQLite y abrirá la plataforma en tu navegador predeterminado en `http://localhost:5005`.

---

## 📚 Cómo Importar Tus Libros PDF (Vocabulario de 1.000 Palabras)

1. Coloca tu archivo PDF en la carpeta:
   ```
   05-english-duo-hub/material/
   ```
2. Ejecuta el extractor automático:
   ```bash
   python scripts/extract_pdf_words.py
   ```
3. El script extraerá las palabras y sus traducciones, y las agregará a la base de datos distribuidas en bloques de 5 palabras por día consecutivo.

---

## 👥 Sistema Dúo (Javier & Compañero)

* Puedes alternar de usuario en la barra superior con un clic: `[Javier]` o `[Compañero]`.
* Cada uno cuenta con su propio registro diario, racha de días cumplidos (*streak*) y resúmenes guardados.
* La barra de responsabilidad muestra en tiempo real cuántos pilares ha completado tu compañero hoy para mantener la motivación mutua.
