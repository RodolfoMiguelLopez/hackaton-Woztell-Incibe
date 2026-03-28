# Asistente de Compras WhatsApp

Asistente personal por WhatsApp para personas mayores. Gestiona el pedido de la compra por voz o texto, con notificación automática al familiar de confianza.

## Enlaces principales

| Recurso | URL |
|---|---|
| Servidor de producción | https://hack-production-435a.up.railway.app |
| Health check | https://hack-production-435a.up.railway.app/health |
| Webhook (Woztell) | https://hack-production-435a.up.railway.app/webhook |
| Debug payloads | https://hack-production-435a.up.railway.app/debug/payloads |
| Debug descarga fichero | https://hack-production-435a.up.railway.app/debug/file/{fileId} |
| Dashboard Railway | https://railway.app |

## Stack

- Python 3.11 + FastAPI + uvicorn
- OpenAI GPT-4o-mini (detección de intención + generación/modificación de lista)
- OpenAI Whisper `whisper-1` (transcripción de audio de voz)
- Woztell WhatsApp API (mensajes + botones interactivos)
- Alojado en Railway (despliegue automático desde GitHub `master`)

## Flujo completo de la demo

### Mensaje de texto

1. Antonio escribe "Quiero hacer la compra" por WhatsApp
2. GPT-4o-mini detecta intención de compra
3. El bot responde con la lista habitual y 3 botones interactivos
4. Antonio pulsa **✅ Confirmar**, **✏️ Modificar** o **❌ Cancelar**
5. Al confirmar: Antonio recibe fecha/hora de entrega y María recibe notificación automática

### Mensaje de audio (voz)

1. Antonio graba y envía un audio de voz por WhatsApp
2. Woztell entrega el webhook con `{"type":"AUDIO","data":{"opus":true,"fileId":"..."}}`
3. El servidor llama a la API GraphQL de Woztell para obtener la URL del fichero:
   ```graphql
   { apiViewer { file(fileId: "xxx") { url } } }
   ```
4. Woztell devuelve una URL pre-firmada de Amazon S3 (`woztell-files.s3.eu-north-1.amazonaws.com/...`)
5. El servidor descarga el audio directamente desde S3 (sin cabecera Authorization — S3 rechaza tokens externos)
6. El audio `.ogg` se envía a OpenAI Whisper `whisper-1` con `language="es"`
7. Whisper devuelve la transcripción en texto
8. A partir de aquí el flujo continúa igual que con texto

### Estados de conversación

```
IDLE ──────────────────────────────────────────────────────────────────────────┐
  │  intención de compra detectada                                              │
  ▼                                                                             │
AWAITING_CONFIRMATION ──── ✅ Confirmar ──► notifica Antonio + María ──► IDLE  │
  │                                                                             │
  ├──── ✏️ Modificar ──► MODIFYING                                             │
  │                           │  nuevo texto/audio con cambios                 │
  │                           └──────────────────────────────► AWAITING_CONFIRMATION
  │                                                                             │
  └──── ❌ Cancelar ──────────────────────────────────────────────────────────►┘
```

## Estructura del proyecto

```
main.py              # FastAPI app + webhook + orquestación de estados
config.py            # Credenciales y configuración (hardcoded para demo)
woztell.py           # Cliente API Woztell (envío de mensajes y botones)
ai_processor.py      # GPT-4o-mini: detección de intención, generación y modificación de lista
audio_processor.py   # Descarga audio vía GraphQL Woztell + transcripción con Whisper
conversation.py      # Estado de conversación en memoria (por número de teléfono)
shopping_list.py     # Lista habitual ficticia de Antonio (categorizada con precios)
tests/               # Suite de tests con pytest-asyncio
Procfile             # web: uvicorn main:app --host 0.0.0.0 --port $PORT
runtime.txt          # python-3.11.9
docs/superpowers/    # Especificación de diseño y plan de implementación
```

## Setup local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Arrancar el servidor
uvicorn main:app --reload --port 8000

# 3. Exponer con ngrok para recibir webhooks de Woztell
ngrok http 8000

# 4. Configurar la URL ngrok como webhook en Woztell
#    Ejemplo: https://abc123.ngrok.io/webhook
```

## Tests

```bash
pytest tests/ -v
```

## Despliegue

El proyecto se despliega automáticamente en Railway al hacer push a `master`.
Railway lee el `Procfile` y `runtime.txt` para configurar el servidor.

## Integración futura con Make

El endpoint `POST /make/trigger` está preparado para recibir eventos de Make como orquestador:

```json
{
  "event": "PURCHASE_INTENT",
  "phone": "34623040432",
  "lista": [...]
}
```
