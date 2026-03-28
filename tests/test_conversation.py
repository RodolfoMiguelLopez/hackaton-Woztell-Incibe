from conversation import get_state, set_state, get_lista, set_lista, reset


def test_estado_inicial_es_idle():
    state = get_state("111111")
    assert state["state"] == "IDLE"
    assert state["current_list"] == []


def test_set_state_cambia_estado():
    set_state("222222", "AWAITING_CONFIRMATION")
    assert get_state("222222")["state"] == "AWAITING_CONFIRMATION"


def test_set_lista_y_get_lista():
    lista = [{"nombre": "Leche", "cantidad": 1, "precio": 0.89, "categoria": "Lácteos"}]
    set_lista("333333", lista)
    assert get_lista("333333") == lista


def test_reset_vuelve_a_idle_y_limpia_lista():
    set_state("444444", "MODIFYING")
    set_lista("444444", [{"nombre": "Pan", "cantidad": 1, "precio": 1.20, "categoria": "Panadería"}])
    reset("444444")
    assert get_state("444444")["state"] == "IDLE"
    assert get_lista("444444") == []
