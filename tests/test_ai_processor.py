import pytest
import config
config.USE_MOCK_AI = True  # forzar modo mock para tests

from ai_processor import detect_intent, generate_shopping_list, modify_list, INTENT_PURCHASE, INTENT_UNKNOWN
from shopping_list import get_lista_completa


async def test_detect_intent_compra():
    assert await detect_intent("quiero hacer la compra") == INTENT_PURCHASE


async def test_detect_intent_unknown():
    assert await detect_intent("hola buenos días") == INTENT_UNKNOWN


async def test_detect_intent_necesito():
    assert await detect_intent("necesito algunas cosas del mercado") == INTENT_PURCHASE


async def test_generate_shopping_list_devuelve_productos():
    lista = await generate_shopping_list("quiero hacer la compra", get_lista_completa())
    assert len(lista) > 0
    assert all("nombre" in p for p in lista)


async def test_modify_list_mas_incrementa_cantidad():
    lista = [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}]
    result = await modify_list(lista, "quiero más leche")
    assert result[0]["cantidad"] == 2


async def test_modify_list_sin_reduce_lista():
    lista = [
        {"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"},
        {"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"},
    ]
    result = await modify_list(lista, "sin el primero")
    assert len(result) == 1
