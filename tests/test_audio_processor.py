import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from audio_processor import transcribe_audio


async def test_transcribe_audio_retorna_texto():
    mock_http_response = MagicMock()
    mock_http_response.content = b"fake ogg audio bytes"
    mock_http_response.raise_for_status = MagicMock()

    mock_transcription = MagicMock()
    mock_transcription.text = "quiero hacer la compra"

    with patch("audio_processor.httpx.AsyncClient") as mock_client_class, \
         patch("audio_processor.openai_client.audio.transcriptions.create", new_callable=AsyncMock) as mock_whisper:

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value = mock_client
        mock_whisper.return_value = mock_transcription

        result = await transcribe_audio("https://fake-url/audio.ogg")
        assert result == "quiero hacer la compra"


async def test_transcribe_audio_devuelve_vacio_si_falla():
    with patch("audio_processor.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        mock_client_class.return_value = mock_client

        result = await transcribe_audio("https://fake-url/audio.ogg")
        assert result == ""
