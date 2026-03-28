# Asistente de Compras WhatsApp

Asistente personal por WhatsApp para personas mayores. Gestiona el pedido de la compra por voz o texto, con notificación automática al familiar de confianza.

## Stack

- Python 3.11 + FastAPI + uvicorn
- OpenAI GPT-4o-mini (intención + lista) + Whisper (transcripción de audio)
- Woztell WhatsApp API

## Setup rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Arrancar el servidor
uvicorn main:app --reload --port 8000

# 3. Exponer con ngrok
ngrok http 8000

# 4. Copiar la URL de ngrok y configurarla como webhook en Woztell
#    Ejemplo: https://abc123.ngrok.io/webhook
```

## Ejecutar tests

```bash
pytest tests/ -v
```

## Flujo de la demo

1. Antonio envía por WhatsApp "Quiero hacer la compra" — por texto **o por audio de voz**
2. El bot responde con la lista habitual y 3 botones
3. **✅ Confirmar** → Antonio recibe confirmación con fecha/hora de entrega + María recibe notificación automática
4. **✏️ Modificar** → Antonio puede cambiar la lista ("sin yogures", "añade más leche") y luego confirmar
5. **❌ Cancelar** → Mensaje amable y vuelta al inicio

## Estructura

```
main.py              # FastAPI app + webhook + orquestación
config.py            # Credenciales y configuración
woztell.py           # Cliente API Woztell
ai_processor.py      # GPT-4o-mini: intención + generación/modificación de lista
audio_processor.py   # Whisper: transcripción de mensajes de audio
conversation.py      # Estado de conversación en memoria
shopping_list.py     # Lista habitual ficticia de Antonio
tests/               # Suite de tests con pytest
```

## Integración futura con Make

El endpoint `POST /make/trigger` está preparado para recibir eventos de Make:

```json
{
  "event": "PURCHASE_INTENT",
  "phone": "34623040432",
  "lista": [...]
}
```
