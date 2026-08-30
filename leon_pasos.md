# Pasos a Seguir para el Desarrollo de L.E.O.N.

Para construir este asistente desde cero de manera estructurada, te recomiendo seguir estos pasos de implementación:

## Fase 1: Entorno y Esqueleto
1. **Configurar el Entorno:** Instalar Python 3.10+ y crear un entorno virtual.
2. **Crear la Estructura del Proyecto:** Carpetas separadas para audios, módulos (skills), configuración y el núcleo del programa.

## Fase 2: Escucha y Transcripción (Oídos)
1. **Implementar Wake Word:** 
   - *Herramienta recomendada:* `Porcupine` (Picovoice) o `PocketSphinx`. Son ligeras y se ejecutan localmente para detectar cuando dices "LEON".
2. **Reconocimiento de Voz (STT):**
   - Una vez activado por la wake word, grabar el audio del usuario.
   - *Herramienta recomendada:* `OpenAI Whisper` (local o API) o `SpeechRecognition` de Python conectado a Google STT.

## Fase 3: El Cerebro (LLM)
1. **Integrar la IA:** 
   - Enviar el texto transcrito a una API de un modelo de lenguaje (como Gemini, GPT-4, etc.).
   - *Herramienta recomendada:* `LangChain` o usar los SDKs oficiales de las APIs.
2. **Gestión de Contexto:** Guardar los últimos mensajes en una lista para que el asistente recuerde de qué estaban hablando.

## Fase 4: La Voz (TTS)
1. **Texto a Voz:**
   - Convertir la respuesta de texto del LLM en audio.
   - *Herramienta recomendada:* `ElevenLabs` (para voces hiperrealistas), `Edge TTS` (gratuito y de buena calidad) o `pyttsx3` (para funcionar sin internet, aunque suena más robótico).
2. **Reproducción:** Reproducir el audio generado en tus altavoces o auriculares.

## Fase 5: Habilidades (Manos)
1. **Function Calling (Llamada a Herramientas):** Configurar el LLM para que entienda que tiene "herramientas" a su disposición.
2. **Crear Scripts:** Escribir funciones en Python para buscar el clima, abrir aplicaciones o leer noticias, y vincularlas al asistente.

## Fase 6: Optimización
1. **Reducir Latencia:** Hacer que las respuestas fluyan por "chunks" (streaming) para que empiece a hablar antes de que termine de generar la respuesta completa.
2. **Interfaz Gráfica (Opcional):** Añadir una pequeña interfaz con PySide6 o Tkinter que muestre animaciones cuando esté escuchando o hablando.
