import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
import config
config.USE_MOCK_AI = True

from main import app
from conversation import set_state, set_lista, reset


async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_webhook_texto_compra_envia_botones():
    reset("34600000001")
    payload = {
        "from": "34600000001",
        "type": "TEXT",
        "data": {"text": "quiero hacer la compra"},
    }
    with patch("main.send_reply_buttons", new_callable=AsyncMock) as mock_buttons:
        mock_buttons.return_value = {"ok": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert mock_buttons.called


async def test_webhook_confirmar_compra_envia_dos_mensajes():
    phone = "34600000002"
    set_state(phone, "AWAITING_CONFIRMATION")
    set_lista(phone, [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}])

    payload = {
        "from": phone,
        "type": "INTERACTIVE",
        "data": {"interactive": {"button_reply": {"id": "CONFIRMAR_COMPRA"}}},
    }
    with patch("main.send_text", new_callable=AsyncMock) as mock_text:
        mock_text.return_value = {"ok": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert mock_text.call_count == 2  # usuario + familiar


async def test_webhook_cancelar_compra():
    phone = "34600000003"
    set_state(phone, "AWAITING_CONFIRMATION")

    payload = {
        "from": phone,
        "data": {"payload": "CANCELAR_COMPRA"},
    }
    with patch("main.send_text", new_callable=AsyncMock) as mock_text:
        mock_text.return_value = {"ok": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert mock_text.called
    from conversation import get_state
    assert get_state(phone)["state"] == "IDLE"


async def test_webhook_sin_phone_retorna_200():
    payload = {"type": "UNKNOWN", "data": {}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200


async def test_make_trigger_retorna_stub():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/make/trigger", json={"event": "PURCHASE_INTENT", "phone": "34623040432"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
