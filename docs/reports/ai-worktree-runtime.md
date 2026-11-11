# Revisión local de Ajustes IA — 2026-10-14

Arranque solicitado por el propietario en `C:\Users\Developer_PC\.codex\worktrees\117d\CRM_CBN`, rama `codex/proveedores-ia`. Frontend en `http://127.0.0.1:5175/#/settings`; backend en `127.0.0.1:8002`. No se modificó la carpeta del chat de diseños ni se detuvieron sus procesos.

## Configuración y operación

- `frontend/package.json` y `frontend/vite.config.ts`: desarrollo en 5175 con puerto estricto y proxy `/api/ai` hacia 8002; el proxy de preview también apunta a 8002.
- `backend/app/modules/ai/api/router.py`: allowlist local de puertos 8002/5175/4173; se conservan las comprobaciones de cliente loopback, Host, Origin y cabecera local. Las pruebas usan 8002/5175.
- Dependencias independientes instaladas desde `frontend/package-lock.json` mediante `npm ci --ignore-scripts --prefer-offline --no-audit --no-fund` y `backend/requirements.lock` mediante el Python de `backend/.venv`. No hay enlaces a dependencias del chat de diseños.
- Procesos ocultos, ligados a loopback. Backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 1 --no-proxy-headers --no-access-log`, con `CRM_AI_OUTBOUND_ENABLED=false`. Frontend: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5175 --strictPort` desde `frontend`.
- Registro nuevo de ownership y logs: `.local/ai-runtime-5175-8002/runtime.json`. No reutilizar los PIDs heredados; los PIDs son evidencia del arranque y deben contrastarse con ejecutable/argumentos antes de detener procesos.

## Evidencia

- Backend: `ruff format --check`, `ruff check` de los dos archivos afectados y `pip check` aprobados.
- `pytest -q tests/test_ai.py -k 'local or remote_client or security or outbound_opt'`: **7 aprobadas, 38 no seleccionadas**.
- Frontend: Prettier check de `vite.config.ts` y `package.json` aprobado.
- HTTP real: ajustes directos 8002 y vía proxy 5175 responden **200**; frontend **200**; salud live **200** y ready **503 esperado**.
- Sin cabecera local, Origin externo y Origin del diseño `http://127.0.0.1:5173`: **403**. Salida IA confirmada deshabilitada en respuesta de ajustes.
- `.local/ai-settings.json` conserva exactamente su SHA-256 anterior al arranque: `94A9DD02BF4333562DB3EB19D8BF3ECF203A254E469061C1889C7557EF77C622`.

El primer intento de dependencias falló por permisos temporales de Python y resolución DNS de npm en sandbox. Se completaron mediante escalación aprobada, acotada al worktree. No se ejecutó una suite global ni se invoca esa evidencia como prueba de navegador. La inspección visual corresponde al coordinador/propietario. Sin llamadas a proveedores, SQL, envíos, commit, push ni despliegue.
