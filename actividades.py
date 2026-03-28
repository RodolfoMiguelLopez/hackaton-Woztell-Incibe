import config

RUTAS = [
    {
        "nombre": "Parque Enrique Tierno Galván",
        "imagen": f"{config.BASE_URL}/img/tierno.jpeg",
        "caption": "¿Quieres ir al Parque Enrique Tierno Galván? 🌳",
        "maps": "https://www.google.com/maps/dir/Digitaliza+Madrid+(Centro+de+Innovaci%C3%B3n),+C.+de+Embajadores,+181,+Arganzuela,+28045+Madrid/Parque+Enrique+Tierno+Galv%C3%A1n,+C.+Meneses,+4,+Arganzuela,+28045+Madrid/@40.3902849,-3.6924029,16z/data=!3m1!4b1!4m14!4m13!1m5!1m1!1s0xd42270071e3f609:0x9c42615f48ee6bba!2m2!1d-3.6928904!2d40.3915483!1m5!1m1!1s0xd421ebc25594ceb:0xc35b94645b458ce6!2m2!1d-3.6838406!2d40.3900397!3e0",
        "notif_familiar": f"{config.NOMBRE_USUARIO} ha decidido dar un paseo al Parque Enrique Tierno Galván.",
    },
    {
        "nombre": "Centro Cultural Casa del Reloj",
        "imagen": f"{config.BASE_URL}/img/centro.jpeg",
        "caption": "¿O prefieres la zona del Centro Cultural Casa del Reloj? 🏛️",
        "maps": "https://www.google.com/maps/dir/Digitaliza+Madrid+(Centro+de+Innovaci%C3%B3n),+C.+de+Embajadores,+181,+Arganzuela,+28045+Madrid/Centro+Cultural+Casa+del+Reloj,+P.%C2%BA+de+la+Chopera,+6-10,+Arganzuela,+28028+Madrid/@40.3930412,-3.6972613,18z/data=!3m1!4b1!4m14!4m13!1m5!1m1!1s0xd42270071e3f609:0x9c42615f48ee6bba!2m2!1d-3.6928904!2d40.3915483!1m5!1m1!1s0xd4228ad28385a43:0x59f641b81d35e0b7!2m2!1d-3.6990868!2d40.392798!3e0",
        "notif_familiar": f"{config.NOMBRE_USUARIO} ha decidido pasear hacia el Centro Cultural Casa del Reloj.",
    },
]

EVENTOS = [
    {
        "nombre": "Exposición Nuevas Cleopatra",
        "detalle": "🎨 *Exposición Nuevas Cleopatra* en Matadero Madrid\n🕔 Hoy de 17:00 a 21:00",
        "imagen": f"{config.BASE_URL}/img/expo.jpeg",
        "payload": "LLEGAR_MATADERO",
        "boton": "Cómo llegar al Matadero",
        "maps": "https://maps.google.com/?q=Matadero+Madrid,+Paseo+de+la+Chopera+14,+Madrid",
        "notif_familiar": f"{config.NOMBRE_USUARIO} va a la exposición Nuevas Cleopatra en el Matadero (17:00–21:00).",
    },
    {
        "nombre": "Charla sobre Conciencia",
        "detalle": "🎤 *Charla sobre Conciencia*\n🕛 Hoy a las 12:00 · Centro Cultural Las Doroteas",
        "imagen": f"{config.BASE_URL}/img/charla.jpeg",
        "payload": "LLEGAR_DOROTEAS",
        "boton": "Cómo llegar a Las Doroteas",
        "maps": "https://maps.google.com/?q=Centro+Cultural+Las+Doroteas,+Madrid",
        "notif_familiar": f"{config.NOMBRE_USUARIO} va a la Charla sobre Conciencia en Las Doroteas (12:00).",
    },
    {
        "nombre": "Concurso de Bachata",
        "detalle": "💃 *Concurso de Bachata*\nDiscoteca Paraíso · Esta noche hasta las 00:00",
        "imagen": f"{config.BASE_URL}/img/disco.jpg",
        "payload": "LLEGAR_PARAISO",
        "boton": "Cómo llegar a Discoteca Paraíso",
        "maps": "https://maps.google.com/?q=Discoteca+Paraiso+Madrid",
        "notif_familiar": f"{config.NOMBRE_USUARIO} va al Concurso de Bachata en la Discoteca Paraíso (hasta las 00:00).",
    },
]

_KW_PASEO = ["paseo", "caminar", "andar", "parque", "ruta", "aire", "naturaleza", "pasear", "camin", "salir a"]
_KW_EVENTO = ["evento", "exposición", "exposicion", "charla", "disco", "concierto", "bailar", "bachata",
              "actividad", "matadero", "doroteas", "cleopatra", "conciencia", "paraíso", "paraiso", "plan"]

_KW_RUTAS = [
    ["tierno", "parque", "galván", "galvan", "primera", "primero"],
    ["centro", "reloj", "chopera", "segunda", "segundo", "cultural"],
]

_KW_EVENTOS = [
    ["matadero", "exposición", "exposicion", "cleopatra", "primera", "primero", "expo"],
    ["charla", "conciencia", "doroteas", "segunda", "segundo"],
    ["bachata", "disco", "paraíso", "paraiso", "tercera", "tercero", "baile", "discoteca"],
]

_PAYLOAD_TO_IDX = {"LLEGAR_MATADERO": 0, "LLEGAR_DOROTEAS": 1, "LLEGAR_PARAISO": 2}


def detectar_tipo_actividad(text: str) -> str:
    t = text.lower()
    if any(k in t for k in _KW_PASEO):
        return "PASEO"
    if any(k in t for k in _KW_EVENTO):
        return "EVENTO"
    return "UNKNOWN"


def detectar_eleccion_ruta(text: str) -> int | None:
    t = text.lower()
    for i, kws in enumerate(_KW_RUTAS):
        if any(k in t for k in kws):
            return i
    return None


def detectar_eleccion_evento(text: str) -> int | None:
    t = text.lower()
    for i, kws in enumerate(_KW_EVENTOS):
        if any(k in t for k in kws):
            return i
    return None


def evento_por_payload(payload: str) -> dict | None:
    idx = _PAYLOAD_TO_IDX.get(payload)
    return EVENTOS[idx] if idx is not None else None


def msg_notif_familiar(actividad_desc: str) -> str:
    return (
        f"Hola {config.NOMBRE_FAMILIAR} 👋 {config.NOMBRE_USUARIO} ha decidido salir hoy.\n"
        f"{actividad_desc}\n"
        f"¡Está bien, está disfrutando de su tiempo libre! 😊"
    )
