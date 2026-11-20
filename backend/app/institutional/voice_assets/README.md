# Ambiente de RinovaPlus — grabaciones v2

Sustituye las pistas procedurales v1 rechazadas por el propietario.

- **Oficina:** Busy Office No People Loop, Fupicat, CC0 1.0.
  https://freesound.org/people/Fupicat/sounds/534123/
  Teléfonos, impresora y actividad de oficina; sin diálogos. Es una composición
  de fuentes CC0 relacionadas por su autor en la página original.
- **Tecleo:** Keyboard Typing.wav, se2001, CC0 1.0.
  https://freesound.org/people/se2001/sounds/523907/
  Grabación de teclado de portátil con Zoom H4N.

Licencia: https://creativecommons.org/publicdomain/zero/1.0/
Procedencia, URLs públicas y SHA-256 de las descargas en `sources.json`.
Se utilizan las versiones de escucha de alta calidad publicadas por Freesound.
Conversión completa a PCM mono 16 kHz, normalización a -24 LUFS/-3 dBTP.
`backend/tools/build_voice_ambience.py` reproduce los WAV desde esas descargas
verificadas; no descarga nada ni se ejecuta en el contenedor.

No requiere ElevenLabs para las pistas ni para volver a mezclarlas. Los faders,
reducción durante la voz, limitador y duración del mensaje se conservan.
No contiene diálogos de usuarios ni se usa para entrenar modelos.
La percepción de realismo requiere la escucha del propietario; no se infiere de
las mediciones técnicas.
