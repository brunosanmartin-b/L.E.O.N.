# Proyecto de Asistente Virtual: L.E.O.N.

## Contexto del Proyecto

El objetivo de este proyecto es desarrollar un asistente virtual altamente interactivo y personalizado, inspirado en JARVIS de Iron Man. A diferencia de los asistentes convencionales, este sistema debe ser capaz de mantener conversaciones fluidas, ejecutar comandos en el sistema local, integrarse con APIs externas y responder a un comando de voz o "wake word" (palabra de activación). 

Para este proyecto, utilizaremos el nombre **L.E.O.N.** (Lógica Estructurada de Operaciones y Navegación).

### Características Principales:
1. **Activación por Voz (Wake Word):** El asistente estará siempre escuchando en segundo plano esperando escuchar su nombre (ej. "Hola LEON") para iniciar el procesamiento completo.
2. **Procesamiento de Lenguaje Natural (NLP):** Uso de modelos de lenguaje avanzados (LLMs) para entender el contexto y generar respuestas naturales.
3. **Ejecución de Acciones:** Capacidad de abrir programas, buscar en la web, leer correos, controlar domótica, etc.
4. **Síntesis de Voz (TTS):** Voces naturales y expresivas para responder al usuario.
5. **Memoria y Contexto:** Capacidad de recordar preferencias del usuario y el contexto de la conversación actual.

---

## Prompt Inicial para otra IA

Si vas a utilizar otra IA (como ChatGPT, Claude, o un modelo local) para ayudarte a programar el núcleo del asistente, aquí tienes un prompt maestro que puedes usar para darle todo el contexto necesario:

> **Prompt Inicial:**
> "Actúa como un Ingeniero de Software Experto en IA y desarrollo en Python. Quiero construir un asistente virtual de escritorio estilo JARVIS llamado 'LEON' (Lógica Estructurada de Operaciones y Navegación). El sistema debe tener las siguientes capacidades principales:
> 1. Activación mediante una 'wake word' (palabra de activación) de forma local para no consumir tokens de API constantemente.
> 2. Transcripción de voz a texto (STT) para entender mis comandos una vez activado.
> 3. Integración con la API de un modelo de lenguaje (como OpenAI, Anthropic o Gemini) para el procesamiento y generación de respuestas, manteniendo un historial de conversación.
> 4. Conversión de texto a voz (TTS) para que me hable con una voz natural.
> 5. Un sistema modular de 'habilidades' (skills) donde pueda añadir funciones en Python (ej. buscar en wikipedia, decir la hora, abrir Spotify).
> 
> Por favor, dame la arquitectura recomendada, las mejores librerías de Python para cada componente (Wake Word, STT, LLM, TTS) y el código base inicial (esqueleto) para conectar estas partes."

---

## Pasos a Seguir para el Desarrollo

Para construir este asistente desde cero de manera estructurada, te recomiendo seguir estos pasos:

### Fase 1: Entorno y Esqueleto
1. **Configurar el Entorno:** Instalar Python 3.10+ y crear un entorno virtual.
2. **Crear la Estructura del Proyecto:** Carpetas separadas para audios, módulos (skills), configuración y el núcleo del programa.

### Fase 2: Escucha y Transcripción (Oídos)
1. **Implementar Wake Word:** 
   - *Herramienta recomendada:* `Porcupine` (Picovoice) o `PocketSphinx`. Son ligeras y se ejecutan localmente para detectar cuando dices "LEON".
2. **Reconocimiento de Voz (STT):**
   - Una vez activado por la wake word, grabar el audio del usuario.
   - *Herramienta recomendada:* `OpenAI Whisper` (local o API) o `SpeechRecognition` de Python conectado a Google STT.

### Fase 3: El Cerebro (LLM)
1. **Integrar la IA:** 
   - Enviar el texto transcrito a una API de un modelo de lenguaje (como Gemini, GPT-4, etc.).
   - *Herramienta recomendada:* `LangChain` o usar los SDKs oficiales de las APIs.
2. **Gestión de Contexto:** Guardar los últimos mensajes en una lista para que el asistente recuerde de qué estaban hablando.

### Fase 4: La Voz (TTS)
1. **Texto a Voz:**
   - Convertir la respuesta de texto del LLM en audio.
   - *Herramienta recomendada:* `ElevenLabs` (para voces hiperrealistas), `Edge TTS` (gratuito y de buena calidad) o `pyttsx3` (para funcionar sin internet, aunque suena más robótico).
2. **Reproducción:** Reproducir el audio generado en tus altavoces o auriculares.

### Fase 5: Habilidades (Manos)
1. **Function Calling (Llamada a Herramientas):** Configurar el LLM para que entienda que tiene "herramientas" a su disposición.
2. **Crear Scripts:** Escribir funciones en Python para buscar el clima, abrir aplicaciones, o leer noticias, y vincularlas al asistente.

### Fase 6: Optimización
1. **Reducir Latencia:** Hacer que las respuestas fluyan por "chunks" (streaming) para que empiece a hablar antes de que termine de generar la respuesta completa.
2. **Interfaz Gráfica (Opcional):** Añadir una pequeña interfaz con PySide6 o Tkinter que muestre animaciones cuando esté escuchando o hablando.
