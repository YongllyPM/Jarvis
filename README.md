# JARVIS AI 🤖

Asistente virtual inteligente para Windows con interfaz bento, control por voz, procesamiento de archivos, agentes de IA y más.

> Basado en el código original de **[Dexter-666](https://github.com/Dexter-666) (JARVIS v1)** — modificado, extendido y mejorado significativamente.

---

## ✨ Mejoras respecto a JARVIS v1 original

| Aspecto | Original (Dexter-666) | Esta versión |
|---------|----------------------|--------------|
| **Interfaz** | Orbe 3D simple | Dashboard bento con widgets, personaje animado (VTuber), sidebar moderna |
| **Chat** | Consola básica | Chat completo con historial, micrófono, stop, archivos adjuntos |
| **Archivos** | No disponible | Carga de PDF, imágenes (OCR), DOCX, previews |
| **Personaje** | Solo esfera | Sprites PNG animados con estados (idle, hablando, pensando, escuchando) |
| **Agentes** | No disponible | Multi-agente con OpenAI, Anthropic, Gemini — cada uno con su personalidad |
| **Telegram** | No disponible | Bot de Telegram integrado con reenvío de mensajes |
| **Widgets** | No disponible | Sistema (CPU/RAM/batería), notas, recordatorios, archivos recientes, música |
| **Tutorial** | No disponible | Tour interactivo de bienvenida con spotlight |
| **Tema** | Tema único | Claro/oscuro intercambiable |
| **Fondo** | Sólido | Gradiente personalizable o imagen de fondo |
| **Instalación** | Manual | `.bat` automatizado con detección de Python, `.venv`, dependencias, acceso directo |

## 🌟 Características

- **Voz y texto**: Escribí o hablale a JARVIS — micrófono con toggle
- **Personaje animado**: Sprites PNG con animaciones de estado
- **Widgets informativos**: CPU/RAM, batería, hora, clima, música, notas, recordatorios
- **Procesamiento de archivos**: PDF, imágenes (OCR), DOCX — arrastrar y soltar
- **Agentes de IA**: Conversaciones paralelas con distintos proveedores (Gemini, OpenAI, Anthropic)
- **Telegram**: Bot integrado que responde desde tu chat de Telegram
- **Atajo global**: Tecla `Insert` para activar JARVIS desde cualquier lugar

## 🛠️ Tecnologías

- **Python 3.12+**
- **PyQt6** + **QtWebEngine** (interfaz gráfica)
- **Google Gemini** (modelo principal)
- **OpenRouter** (fallback multi-modelo)
- **Vosk** (reconocimiento de voz offline)
- **Tesseract** (OCR)
- **Sounddevice** (audio)

## 🚀 Instalación

1. Instalá [Python 3.12](https://www.python.org/downloads/) (marcar "Add Python to PATH")
2. Ejecutá **`Instalar_JARVIS.bat`** como Administrador
3. Seguí el asistente — crea `.venv`, instala dependencias y genera acceso directo
4. Iniciá desde el acceso directo del escritorio o con **`Iniciar JARVIS Beta.vbs`**

## 🧹 Desinstalar

Ejecutá **`Desinstalar_JARVIS.bat`** — modo ligero (solo `.venv` y caché) o completo.

## 🔐 Seguridad

- Las API keys se guardan localmente en `config/api_keys.json`
- Ese archivo **nunca se sube** a GitHub (protegido por `.gitignore`)

---

👤 **Creado por Yonglly**  
📦 Basado en el código original de **Dexter-666** (JARVIS v1)  
💡 Modificado y mejorado con nuevas funcionalidades
