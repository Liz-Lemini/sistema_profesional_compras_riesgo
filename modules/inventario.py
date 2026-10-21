"""Gestión y análisis de existencias con movimientos trazables."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .storage import next_record_id, read_json_file, write_json_file


INVENTORY_FILE = "inventario.json"
MOVEMENTS_FILE = "movimientos_inventario.json"
MOVEMENT_TYPES = {"Entrada", "Salida", "Ajuste"}


def load_inventory() -> list[dict[str, Any]]:
    data = read_json_file(INVENTORY_FILE, default_data=[])
    return data if isinstance(data, list) else []


def load_inventory_movements() -> list[dict[str, Any]]:
    data = read_json_file(MOVEMENTS_FILE, default_data=[])
    return data if isinstance(data, list) else []


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} debe ser un número entero positivo.")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} debe ser un número entero positivo.") from error
    if not number.is_integer() or number <= 0:
        raise ValueError(f"{field_name} debe ser un número entero positivo.")
    return int(number)


def _non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} debe ser un número entero no negativo.")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} debe ser un número entero no negativo.") from error
    if not number.is_integer() or number < 0:
        raise ValueError(f"{field_name} debe ser un número entero no negativo.")
    return int(number)


def _movement_level(days_without_movement: int) -> str:
    if days_without_movement >= 120:
        return "Critico"
    if days_without_movement >= 90:
        return "Alto"
    return "Controlado"


def _movement_color(level: str) -> str:
    return {
        "Critico": "danger",
        "Alto": "warning",
        "Controlado": "success",
    }.get(level, "secondary")


def _inventory_item(item: dict[str, Any]) -> dict[str, Any]:
    """Devuelve una vista consistente sin modificar registros heredados."""

    stock_actual = int(item.get("stock_actual", 0) or 0)
    stock_minimo = int(item.get("stock_minimo", 0) or 0)
    return {
        **item,
        "stock_actual": stock_actual,
        "stock_minimo": stock_minimo,
        "valor_unitario": float(item.get("valor_unitario", 0) or 0),
        "dias_sin_movimiento": int(item.get("dias_sin_movimiento", 0) or 0),
        "existencia_baja": stock_actual <= stock_minimo,
    }


def list_inventory() -> list[dict[str, Any]]:
    return [_inventory_item(item) for item in load_inventory()]


def list_inventory_movements(sku: str = "") -> list[dict[str, Any]]:
    normalized_sku = sku.strip().casefold()
    movements = load_inventory_movements()
    if normalized_sku:
        movements = [
            movement
            for movement in movements
            if str(movement.get("sku", "")).strip().casefold() == normalized_sku
        ]
    return sorted(
        movements,
        key=lambda movement: (
            str(movement.get("fecha", "")),
            int(movement.get("id", 0) or 0),
        ),
        reverse=True,
    )


def create_inventory_movement(
    payload: dict[str, Any],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Registra una entrada o salida y actualiza la existencia del SKU."""

    today = reference_date or date.today()
    sku = str(payload.get("sku", "")).strip()
    if not sku:
        raise ValueError("El SKU es obligatorio.")

    movement_type = str(payload.get("tipo", "")).strip().title()
    if movement_type not in MOVEMENT_TYPES:
        raise ValueError("El tipo de movimiento debe ser Entrada, Salida o Ajuste.")

    if movement_type == "Ajuste":
        direction = str(payload.get("direccion", "")).strip().title()
        if direction not in {"Incremento", "Decremento"}:
            raise ValueError("Un ajuste debe indicar Incremento o Decremento.")
    else:
        direction = "Incremento" if movement_type == "Entrada" else "Decremento"

    quantity = _positive_integer(payload.get("cantidad"), "La cantidad")
    movement_date_text = str(payload.get("fecha", today.isoformat())).strip()
    try:
        movement_date = _parse_date(movement_date_text)
    except (TypeError, ValueError) as error:
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD.") from error
    if movement_date > today:
        raise ValueError("La fecha del movimiento no puede ser futura.")

    items = load_inventory()
    movements = load_inventory_movements()
    origin_type = str(payload.get("origen_tipo", "")).strip()
    origin_id = payload.get("origen_id")
    if origin_type and origin_id not in (None, "") and any(
        movement.get("origen_tipo") == origin_type
        and str(movement.get("origen_id")) == str(origin_id)
        and movement.get("sku") == sku
        for movement in movements
    ):
        raise ValueError("Este origen ya generó un movimiento para el SKU.")
    item = next(
        (
            candidate
            for candidate in items
            if str(candidate.get("sku", "")).strip().casefold() == sku.casefold()
        ),
        None,
    )
    if item is None:
        raise ValueError("El SKU no existe en el inventario.")

    current_stock = _non_negative_integer(item.get("stock_actual", 0), "La existencia actual")
    decreases_stock = movement_type == "Salida" or (movement_type == "Ajuste" and direction == "Decremento")
    if decreases_stock and quantity > current_stock:
        raise ValueError("La salida no puede ser mayor que la existencia actual.")

    if "stock_inicial" not in item:
        item["stock_inicial"] = current_stock
    item["stock_actual"] = current_stock - quantity if decreases_stock else current_stock + quantity
    item["dias_sin_movimiento"] = max((today - movement_date).days, 0)
    item["fecha_ultima_movimiento"] = movement_date.isoformat()

    movement = {
        "id": next_record_id(movements),
        "sku": item.get("sku", sku),
        "tipo": movement_type,
        "direccion": direction,
        "cantidad": quantity,
        "fecha": movement_date.isoformat(),
        "origen_tipo": origin_type,
        "origen_id": origin_id,
        "referencia": str(payload.get("referencia", "")).strip(),
        "proceso_id": payload.get("proceso_id"),
        "orden_id": payload.get("orden_id"),
        "observaciones": str(payload.get("observaciones", "")).strip(),
    }

    write_json_file(INVENTORY_FILE, items)
    movements.append(movement)
    write_json_file(MOVEMENTS_FILE, movements)
    return {**movement, "stock_actual": item["stock_actual"]}


def build_inventory_dashboard(reference_date: date | None = None) -> dict[str, Any]:
    today = reference_date or date.today()
    inventory = list_inventory()
    movements = list_inventory_movements()

    lagged_items: list[dict[str, Any]] = []
    for item in inventory:
        stock_actual = item["stock_actual"]
        stock_minimo = item["stock_minimo"]
        unit_value = item["valor_unitario"]
        days_without_movement = item["dias_sin_movimiento"]
        immobilized_value = round(stock_actual * unit_value, 2)
        excess_units = max(stock_actual - stock_minimo, 0)
        excess_value = round(excess_units * unit_value, 2)
        level = _movement_level(days_without_movement)

        if days_without_movement >= 90:
            lagged_items.append(
                {
                    "sku": item.get("sku"),
                    "descripcion": item.get("descripcion"),
                    "categoria": item.get("categoria"),
                    "stock_actual": stock_actual,
                    "stock_minimo": stock_minimo,
                    "dias_sin_movimiento": days_without_movement,
                    "valor_inmovilizado": immobilized_value,
                    "exceso_unidades": excess_units,
                    "valor_exceso": excess_value,
                    "nivel_resago": level,
                    "color": _movement_color(level),
                    "proveedor_principal": item.get("proveedor_principal"),
                }
            )

    lagged_items.sort(
        key=lambda item: (item["valor_inmovilizado"], item["dias_sin_movimiento"]),
        reverse=True,
    )

    total_immobilized_value = round(
        sum(item["valor_inmovilizado"] for item in lagged_items),
        2,
    )
    total_excess_value = round(sum(item["valor_exceso"] for item in lagged_items), 2)

    return {
        "fecha_corte": today.isoformat(),
        "resumen": {
            "items_monitoreados": len(inventory),
            "inventario_rezagado": len(lagged_items),
            "inventario_bajo": sum(item["existencia_baja"] for item in inventory),
            "capital_inmovilizado": total_immobilized_value,
            "valor_exceso": total_excess_value,
            "movimientos": len(movements),
        },
        "inventario": inventory,
        "inventario_rezagado": lagged_items,
        "movimientos": movements[:50],
    }
