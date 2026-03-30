import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from woztell import send_text, send_message

PHONE = "34XXXXXXXXX"


async def test_send_message_llama_a_woztell():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": 1}
    mock_response.raise_for_status = MagicMock()

    with patch("woztell.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await send_message(PHONE, [{"type": "TEXT", "text": "Hola"}])
        assert result["ok"] == 1
        assert mock_client.post.called


async def test_send_text_construye_payload_correcto():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": 1}
    mock_response.raise_for_status = MagicMock()

    with patch("woztell.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await send_text(PHONE, "Texto de prueba")
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["recipientId"] == PHONE
        assert payload["response"][0]["type"] == "TEXT"
        assert payload["response"][0]["text"] == "Texto de prueba"
