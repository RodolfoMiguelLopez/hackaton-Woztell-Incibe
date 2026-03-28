# Diseño: Asistente de Compras por WhatsApp para Personas Mayores

**Fecha:** 2026-03-28
**Contexto:** Hackathon — MVP funcional en una sesión
**Stack:** Python 3.11 + FastAPI + OpenAI API (GPT-4o-mini + Whisper) + Woztell WhatsApp API

---

## 1. Objetivo

Construir un servidor webhook en Python que actúe como asistente personal de compras para personas mayores vía WhatsApp. El usuario puede escribir **o hablar** (mensaje de audio); el sistema transcribe el audio automáticamente con Whisper, interpreta la intención, genera una lista de compra personalizada, pide confirmación mediante botones interactivos y, al confirmar, notifica tanto al usuario como a un familiar de confianza.

---

## 2. Arquitectura

### Topología

```
WhatsApp → Woztell → POST /webhook ←── ngrok ──← FastAPI (puerto 8000)
                                                        │
                               ┌────────────────────────┼──────────────────────────┐
                               │                        │                          │
                          woztell.py             ai_processor.py          conversation.py
                        (envía mensajes)        (OpenAI / mock)          (estado en dict)
                               │                        │
                         shopping_list.py        audio_processor.py
                         (lista ficticia)       (Whisper transcripción)
```

### Endpoints FastAPI

| Endpoint | Método | Propósito |
|---|---|---|
| `/webhook` | POST | Recibe mensajes entrantes de Woztell (WhatsApp) |
| `/make/trigger` | POST | Punto de extensión para Make como orquestador (futura iteración) |
| `/health` | GET | Health check |

### Contrato `/make/trigger`

```json
// Request
POST /make/trigger
{
  "event": "PURCHASE_INTENT",        // PURCHASE_INTENT | CONFIRM | CANCEL
  "phone": "34623040432",            // teléfono del usuario
  "lista": [                         // opcional, solo en PURCHASE_INTENT
    {"nombre": "Leche", "cantidad": 2, "precio": 0.89, "categoria": "Lácteos"}
  ]
}

// Response
{"ok": true, "state": "AWAITING_CONFIRMATION"}
// o en error:
{"ok": false, "error": "descripción"}
```

En la iteración actual el endpoint existe, loguea la llamada y retorna `{"ok": true, "state": "stub"}`. Sin autenticación por ahora (hackathon).

---

## 3. Estructura de datos

### Objeto de estado por usuario (`conversation.py`)

```python
# Dict global: phone (str) → ConversationState
ConversationState = {
    "state": "IDLE",              # IDLE | AWAITING_CONFIRMATION | MODIFYING
    "current_list": [],           # lista actual de productos
    "timestamp": datetime,        # última actualización
}

# Valor inicial cuando se crea un usuario nuevo:
DEFAULT_STATE = {"state": "IDLE", "current_list": [], "timestamp": None}
```

### Estructura de un producto en la lista

```python
Producto = {
    "nombre": str,       # e.g. "Leche semidesnatada"
    "cantidad": int,     # e.g. 2
    "precio": float,     # precio unitario, e.g. 0.89
    "categoria": str,    # e.g. "Lácteos"
}
```

---

## 4. Módulos y contratos de interfaz

### `audio_processor.py`

```python
async def transcribe_audio(audio_url: str) -> str:
    """
    Descarga el archivo de audio desde audio_url (OGG/Opus que envía WhatsApp)
    y lo transcribe usando la API de OpenAI Whisper (model="whisper-1").

    Flujo interno:
    1. GET audio_url con header Authorization: Bearer WOZTELL_ACCESS_TOKEN
       (Woztell sirve los audios autenticados)
    2. Guarda en fichero temporal con sufijo .ogg
    3. Llama a openai.audio.transcriptions.create(model="whisper-1", file=..., language="es")
    4. Elimina el fichero temporal
    5. Retorna el texto transcrito (str)

    En caso de error: loguea el error y retorna "" (cadena vacía)
    """
```

**Nota:** Whisper acepta OGG/Opus directamente — no se necesita conversión de formato.

### `config.py`
Variables de configuración centralizadas. Sin lógica. Valores hardcodeados en el fichero (hackathon — no se usa `.env` para simplificar el setup).

```python
OPENAI_API_KEY = "sk-proj-..."       # API key de OpenAI
OPENAI_MODEL = "gpt-4o-mini"         # modelo a usar
WOZTELL_ACCESS_TOKEN = "eyJ..."      # token JWT de Woztell Bot API
WOZTELL_CHANNEL_ID = "69845cf3e2606f35bb7d9547"
WOZTELL_BOT_API_URL = "https://bot.api.woztell.com/sendResponses"
TELEFONO_USUARIO = "34623040432"     # teléfono del usuario (Antonio)
TELEFONO_FAMILIAR = "34669295504"    # teléfono del familiar (María) — fijo, hardcodeado
NOMBRE_USUARIO = "Antonio"
NOMBRE_FAMILIAR = "María"
USE_MOCK_AI = False                  # True = usa mock sin llamar a OpenAI
WOZTELL_RETRY_DELAY_SECONDS = 1      # segundos entre reintento a Woztell
PORT = 8000                          # uvicorn main:app --port 8000
```

**Arranque:** `uvicorn main:app --reload --port 8000`. Single-process obligatorio — el estado de conversación está en memoria RAM; múltiples workers de Gunicorn corromperían el estado. Reiniciar el proceso borra todas las conversaciones activas (aceptable para demo).

### `shopping_list.py`

```python
LISTA_HABITUAL: dict[str, list[Producto]]  # categoría → lista de productos

def get_lista_completa() -> list[Producto]:
    """Devuelve todos los productos de LISTA_HABITUAL como lista plana."""

def format_summary(lista: list[Producto]) -> str:
    """
    Genera texto legible para WhatsApp.
    Ejemplo de salida:
    🛒 *Tu lista de la compra:*
    • Lácteos: Leche semidesnatada x2, Yogures x1
    • Panadería: Pan integral x1
    💰 Total estimado: 8,43 €
    """

def calcular_total(lista: list[Producto]) -> float:
    """Suma precio × cantidad para cada producto. Retorna float redondeado a 2 decimales."""
```

### `conversation.py`

```python
def get_state(phone: str) -> ConversationState:
    """Retorna estado actual. Si el phone no existe, crea DEFAULT_STATE."""

def set_state(phone: str, state: str) -> None:
    """Actualiza el campo 'state'. Valores válidos: IDLE, AWAITING_CONFIRMATION, MODIFYING."""

def get_lista(phone: str) -> list[Producto]:
    """Retorna current_list del usuario."""

def set_lista(phone: str, lista: list[Producto]) -> None:
    """Reemplaza current_list del usuario."""

def reset(phone: str) -> None:
    """Vuelve a IDLE y vacía current_list."""
```

### `woztell.py`

```python
async def send_text(recipient: str, text: str) -> dict:
    """Envía mensaje de texto simple. Reintenta 1 vez tras WOZTELL_RETRY_DELAY_SECONDS si falla."""

async def send_reply_buttons(
    recipient: str,
    body: str,
    footer: str,
    buttons: list[dict]  # [{"payload": str, "title": str}]
) -> dict:
    """Envía mensaje con botones de respuesta (máx 3)."""

async def send_message(recipient: str, responses: list[dict]) -> dict:
    """Función de bajo nivel. Llama POST /sendResponses. Retorna respuesta de Woztell."""
```

### `ai_processor.py`

```python
# Intents posibles
INTENT_PURCHASE = "PURCHASE_INTENT"
INTENT_UNKNOWN = "UNKNOWN"

async def detect_intent(text: str) -> str:
    """
    Detecta intención del mensaje. Retorna INTENT_PURCHASE o INTENT_UNKNOWN.

    Mock (USE_MOCK_AI=True): retorna INTENT_PURCHASE si el texto (en minúsculas) contiene
    alguna de: ["compra", "comprar", "necesito", "lista", "mercado", "super",
                "supermercado", "quiero", "pedir", "pedido"]
    En caso contrario retorna INTENT_UNKNOWN.

    OpenAI: prompt del sistema instruye a responder solo "PURCHASE_INTENT" o "UNKNOWN".
    """

async def generate_shopping_list(
    user_message: str,
    lista_habitual: list[Producto]
) -> list[Producto]:
    """
    Genera lista de compra basada en LISTA_HABITUAL.
    OpenAI recibe el mensaje del usuario + lista habitual como JSON y puede ajustar cantidades.

    Mock (USE_MOCK_AI=True): retorna get_lista_completa() sin modificar
    (todos los productos de LISTA_HABITUAL con cantidades y precios por defecto).

    Retorna list[Producto].
    """

async def modify_list(
    current_lista: list[Producto],
    modification_text: str
) -> list[Producto]:
    """
    Reinterpreta current_lista según el texto de modificación del usuario.

    Mock (USE_MOCK_AI=True):
      - Contiene "más" o "añade": incrementa en 1 la cantidad del primer producto
      - Contiene "sin" o "quita": elimina el primer producto de la lista
      - Cualquier otro texto: retorna current_lista sin cambios

    Retorna list[Producto] modificada.
    """
```

---

## 5. Máquina de estados

```
IDLE
  │  usuario envía texto con intención de compra
  │  → detect_intent() = PURCHASE_INTENT
  │  → generate_shopping_list()
  │  → send_reply_buttons() con resumen + 3 botones
  ▼
AWAITING_CONFIRMATION
  │
  ├─ payload = CONFIRMAR_COMPRA
  │    → send_text(usuario, mensaje_confirmacion)
  │    → send_text(familiar, mensaje_familiar)      ← notificación al familiar
  │    → reset(phone) → IDLE
  │
  ├─ payload = CANCELAR_COMPRA
  │    → send_text(usuario, mensaje_cancelacion)
  │    → reset(phone) → IDLE
  │
  └─ payload = MODIFICAR_COMPRA
       → send_text(usuario, "¿Qué te gustaría cambiar?...")
       → set_state(phone, MODIFYING)
       ▼
      MODIFYING
        │
        ├─ texto libre válido
        │    → modify_list(current_lista, texto)
        │    → send_reply_buttons() con nueva lista + 3 botones
        │    → set_state(phone, AWAITING_CONFIRMATION)
        │
        └─ texto no reconocible, "cancelar" o "no"
             → send_text(usuario, mensaje_cancelacion)
             → reset(phone) → IDLE
```

**Nota:** En estado MODIFYING, si el texto no genera una lista válida o contiene "cancelar"/"no", se cancela directamente y vuelve a IDLE. Sin contador de intentos (simplicidad para hackathon).

### Botones enviados en AWAITING_CONFIRMATION

```json
[
  {"payload": "CONFIRMAR_COMPRA", "title": "✅ Confirmar"},
  {"payload": "MODIFICAR_COMPRA", "title": "✏️ Modificar"},
  {"payload": "CANCELAR_COMPRA",  "title": "❌ Cancelar"}
]
```

---

## 6. Mensajes al usuario y al familiar

### Confirmación al usuario (Antonio)

```
¡Perfecto, Antonio! 🛒 Tu pedido está confirmado.
El repartidor lo dejará en tu domicilio mañana {fecha_str} entre las 10:00 y las 12:00.
¡Asegúrate de estar en casa! 😊
```

- `fecha_str`: fecha del día siguiente en formato "martes 29 de marzo" (calculada dinámicamente con `datetime.now() + timedelta(days=1)`)

### Notificación al familiar (María)

```
Hola María 👋 Antonio acaba de confirmar su pedido de la compra.
Se lo entregarán mañana {fecha_str} entre las 10:00 y las 12:00 en su domicilio.
Por si quieres pasarte a ayudarle con las bolsas. ¡Gracias! 😊
```

- Se envía con `send_text(TELEFONO_FAMILIAR, mensaje_familiar)` inmediatamente tras la confirmación del usuario.

### Cancelación

```
De acuerdo, Antonio. He cancelado el pedido.
Si en otro momento quieres hacer la compra, ¡aquí estaré! 😊
```

---

## 7. Parsing defensivo del webhook de Woztell

El payload completo se loguea siempre antes de procesarlo. Extracción en este orden de prioridad:

```python
body = await request.json()
logger.info(f"[WEBHOOK] Payload completo: {json.dumps(body)}")

# 1. Número de teléfono del remitente
phone = (
    body.get("from")
    or body.get("sender", {}).get("phone")
    or body.get("member")
)

# 2. Tipo de mensaje
msg_type = body.get("type", "").upper()  # "TEXT", "AUDIO", "VOICE", "INTERACTIVE", etc.

# 3. Texto libre del usuario (mensajes de texto)
text = (
    body.get("data", {}).get("text")           # formato estándar Woztell
    or body.get("text")                         # variante flat
    or body.get("message", {}).get("text")      # variante anidada
    or body.get("data", {}).get("body")         # variante body
)

# 4. URL del audio (mensajes de voz)
audio_url = (
    body.get("data", {}).get("url")                          # URL directa Woztell
    or body.get("data", {}).get("audio", {}).get("url")      # anidado
    or body.get("data", {}).get("voice", {}).get("url")      # tipo voice
    or body.get("data", {}).get("link")                      # variante link
)

# 5. Payload de botón pulsado
button_payload = (
    body.get("data", {}).get("interactive", {}).get("button_reply", {}).get("id")
    or body.get("data", {}).get("payload")
    or body.get("data", {}).get("button_reply", {}).get("id")
    or body.get("payload")
    or body.get("postback", {}).get("payload")
)
```

### Lógica de resolución en `main.py`

```python
if button_payload:
    # mensaje de botón → manejar según estado
    handle_button(phone, button_payload)

elif audio_url or msg_type in ("AUDIO", "VOICE"):
    # mensaje de audio → transcribir con Whisper → procesar como texto
    transcribed = await transcribe_audio(audio_url)
    if transcribed:
        handle_text(phone, transcribed)
    else:
        send_text(phone, "Lo siento, no he podido escuchar bien el audio. ¿Puedes repetirlo o escribirlo? 🙏")

elif text:
    # mensaje de texto normal
    handle_text(phone, text)

else:
    logger.warning(f"UNPARSED_PAYLOAD (phone: {phone}): {body}")
    # retornar HTTP 200 sin responder
```

Si `phone` es None → ignorar la llamada y retornar HTTP 200 (evitar reintentos de Woztell).

---

## 8. Manejo de errores

| Situación | Comportamiento |
|---|---|
| Woztell devuelve `ok: 0` | Log de error con código, reintento tras 1s, 1 sola vez |
| OpenAI falla o timeout | Log de error, enviar al usuario: "Lo siento, Antonio, ha habido un problema. ¿Puedes intentarlo de nuevo?" |
| Payload webhook no reconocido | Log `UNPARSED_PAYLOAD` con body completo, retornar HTTP 200 |
| Estado inconsistente | reset(phone) → IDLE, mensaje pidiendo que repita |
| phone no encontrado en payload | Ignorar silenciosamente, HTTP 200 |

---

## 9. Logging

Formato: `[ESTADO] → [ACCIÓN] → [RESULTADO] (phone: XXXXX)`

Ejemplos:
```
[IDLE] → detect_intent("quiero hacer la compra") → PURCHASE_INTENT (phone: 34623040432)
[IDLE] → generate_shopping_list() → 14 productos, total 27.31€ (phone: 34623040432)
[IDLE] → send_reply_buttons() → ok (phone: 34623040432)
[AWAITING_CONFIRMATION] → CONFIRMAR_COMPRA recibido (phone: 34623040432)
[AWAITING_CONFIRMATION] → send_text(usuario) → ok (phone: 34623040432)
[AWAITING_CONFIRMATION] → send_text(familiar) → ok (phone: 34623040432)
```

---

## 10. Configuración y arranque

```bash
pip install -r requirements.txt
# Editar config.py con credenciales
uvicorn main:app --reload --port 8000
ngrok http 8000
# Copiar URL de ngrok → configurar como webhook en Woztell
```

### `requirements.txt`

```
fastapi
uvicorn[standard]
httpx
openai
```

(`python-dotenv` eliminado — no se usa `.env` en esta versión hackathon)

---

## 11. Estructura de ficheros

```
hackathon-asistente/
├── main.py              # FastAPI app + endpoints + orquestación del flujo
├── config.py            # Variables de configuración y credenciales
├── woztell.py           # Cliente API Woztell (envío de mensajes)
├── ai_processor.py      # Lógica OpenAI GPT-4o-mini + mock
├── audio_processor.py   # Transcripción de audio con OpenAI Whisper
├── conversation.py      # Gestión de estado en memoria
├── shopping_list.py     # Lista habitual ficticia + utilidades
├── requirements.txt     # Dependencias Python
└── README.md            # Setup rápido para la demo
```

---

## 12. Criterios de éxito para la demo

1. Usuario envía "quiero hacer la compra" por texto **o por audio de voz** → el audio se transcribe automáticamente y el sistema responde con la lista y 3 botones (Confirmar / Modificar / Cancelar)
2. Usuario pulsa "✅ Confirmar" → recibe mensaje de confirmación con fecha del día siguiente (formato "martes 29 de marzo") y franja horaria 10:00-12:00
3. Familiar (34669295504) recibe notificación automática en el mismo momento que el usuario confirma, sin intervención manual
4. Usuario pulsa "✏️ Modificar" → puede enviar texto libre ("sin yogures", "añade más leche") → recibe nueva lista actualizada con botones
5. Usuario pulsa "❌ Cancelar" → recibe mensaje amable y el sistema vuelve a IDLE
6. Consola muestra logs legibles con formato `[ESTADO] → [ACCIÓN] → [RESULTADO]` para cada paso del flujo

---

## 13. Futura integración Make (siguiente iteración)

1. Make se suscribe al webhook de Woztell directamente
2. Make procesa la intención (módulo OpenAI nativo de Make)
3. Make llama a `POST /make/trigger` con la lista generada
4. El servidor Python gestiona estado y envía mensajes a Woztell
5. No requiere cambios en `woztell.py`, `conversation.py` ni `shopping_list.py`
