# Prompt Inicial para otra IA

Si vas a utilizar otra IA (como ChatGPT, Claude o un modelo local) para ayudarte a programar el núcleo del asistente L.E.O.N., aquí tienes el prompt maestro listo para copiar y pegar:

```text
Actúa como un Ingeniero de Software Experto en IA y desarrollo en Python. Quiero construir un asistente virtual de escritorio estilo JARVIS llamado 'LEON' (Lógica Estructurada de Operaciones y Navegación). El sistema debe tener las siguientes capacidades principales:

1. Activación mediante una 'wake word' (palabra de activación) de forma local para no consumir tokens de API constantemente.
2. Transcripción de voz a texto (STT) para entender mis comandos una vez activado.
3. Integración con la API de un modelo de lenguaje (como OpenAI, Anthropic o Gemini) para el procesamiento y generación de respuestas, manteniendo un historial de conversación.
4. Conversión de texto a voz (TTS) para que me hable con una voz natural.
5. Un sistema modular de 'habilidades' (skills) donde pueda añadir funciones en Python (ej. buscar en wikipedia, decir la hora, abrir Spotify).

Por favor, dame la arquitectura recomendada, las mejores librerías de Python para cada componente (Wake Word, STT, LLM, TTS) y el código base inicial (esqueleto) para conectar estas partes.
```
