from shopping_list import get_lista_completa, format_summary, calcular_total


def test_get_lista_completa_devuelve_productos():
    lista = get_lista_completa()
    assert len(lista) > 0
    assert all("nombre" in p and "cantidad" in p and "precio" in p and "categoria" in p for p in lista)


def test_calcular_total_suma_correctamente():
    lista = [
        {"nombre": "Leche", "cantidad": 2, "precio": 0.89, "categoria": "Lácteos"},
        {"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"},
    ]
    assert calcular_total(lista) == round(2 * 0.89 + 1.20, 2)


def test_format_summary_contiene_total():
    lista = get_lista_completa()
    summary = format_summary(lista)
    assert "Total" in summary or "total" in summary
    assert "€" in summary


def test_format_summary_contiene_productos():
    lista = [{"nombre": "Leche", "cantidad": 2, "precio": 0.89, "categoria": "Lácteos"}]
    summary = format_summary(lista)
    assert "Leche" in summary
