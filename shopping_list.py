LISTA_HABITUAL = {
    "Lácteos": [
        {"nombre": "Leche semidesnatada", "cantidad": 2, "precio": 0.89},
        {"nombre": "Yogures naturales (pack 8)", "cantidad": 1, "precio": 2.10},
    ],
    "Panadería": [
        {"nombre": "Pan integral", "cantidad": 1, "precio": 1.20},
        {"nombre": "Magdalenas", "cantidad": 1, "precio": 1.50},
    ],
    "Frutas y verduras": [
        {"nombre": "Plátanos (1kg)", "cantidad": 1, "precio": 1.35},
        {"nombre": "Manzanas (1kg)", "cantidad": 1, "precio": 1.89},
        {"nombre": "Tomates (1kg)", "cantidad": 1, "precio": 1.99},
        {"nombre": "Cebollas (malla)", "cantidad": 1, "precio": 1.10},
    ],
    "Proteínas": [
        {"nombre": "Huevos (docena)", "cantidad": 1, "precio": 2.30},
        {"nombre": "Pechuga de pollo (bandeja)", "cantidad": 1, "precio": 3.50},
    ],
    "Despensa": [
        {"nombre": "Aceite de oliva (1L)", "cantidad": 1, "precio": 5.99},
        {"nombre": "Arroz (1kg)", "cantidad": 1, "precio": 1.15},
        {"nombre": "Pasta (500g)", "cantidad": 1, "precio": 0.85},
    ],
    "Limpieza e higiene": [
        {"nombre": "Papel higiénico (pack 12)", "cantidad": 1, "precio": 3.99},
        {"nombre": "Jabón de manos", "cantidad": 1, "precio": 1.50},
    ],
}


def get_lista_completa() -> list[dict]:
    """Devuelve todos los productos de LISTA_HABITUAL como lista plana con campo 'categoria'."""
    productos = []
    for categoria, items in LISTA_HABITUAL.items():
        for item in items:
            productos.append({**item, "categoria": categoria})
    return productos


def calcular_total(lista: list[dict]) -> float:
    """Suma precio × cantidad para cada producto. Retorna float redondeado a 2 decimales."""
    return round(sum(p["precio"] * p["cantidad"] for p in lista), 2)


def format_summary(lista: list[dict]) -> str:
    """Genera texto legible para WhatsApp con la lista agrupada por categoría y el total."""
    por_categoria: dict[str, list[dict]] = {}
    for p in lista:
        cat = p.get("categoria", "Otros")
        por_categoria.setdefault(cat, []).append(p)

    lines = ["🛒 *Tu lista de la compra:*\n"]
    for cat, productos in por_categoria.items():
        items_str = ", ".join(f"{p['nombre']} x{p['cantidad']}" for p in productos)
        lines.append(f"• *{cat}:* {items_str}")

    total = calcular_total(lista)
    lines.append(f"\n💰 *Total estimado: {total:.2f} €*")
    return "\n".join(lines)
