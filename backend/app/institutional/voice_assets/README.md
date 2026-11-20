# Ambiente de RinovaPlus

Dos pistas originales sintetizadas por `backend/tools/build_voice_ambience.py`:
aire/ventilación de oficina y pulsaciones irregulares de teclado. No contienen
conversaciones, grabaciones personales ni audio de terceros. Duración: 20 segundos,
PCM mono 16 kHz. Se repiten únicamente hasta la duración de la voz.

No son sonidos generados por ElevenLabs y no consumen caracteres del proveedor.
La compresión lateral de FFmpeg reduce ambas pistas cuando detecta la voz antes
de aplicar su volumen. La mezcla final conserva la duración, mono OGG/Opus y un
limitador de picos. Referencia: https://ffmpeg.org/ffmpeg-filters.html#sidechaincompress
