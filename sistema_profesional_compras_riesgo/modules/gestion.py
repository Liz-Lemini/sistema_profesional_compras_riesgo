"""Operaciones de captura y consulta para compras y proveedores."""

from __future__ import annotations

from datetime import date
from typing import Any

from .analisis import (
    PURCHASES_FILE,
    SUPPLIERS_FILE,
    calculate_remaining_days,
    load_purchases,
    load_suppliers,
    parse_date,
)
from .storage import next_record_id, write_json_file


def _clean_text(value: Any, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"El campo '{field_name}' es obligatorio.")
    return cleaned


def _clean_positive_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser numerico.") from error

    if number <= 0:
        raise ValueError(f"El campo '{field_name}' debe ser mayor a cero.")

    return round(number, 2)


def _clean_positive_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser entero.") from error

    if number <= 0:
        raise ValueError(f"El campo '{field_name}' debe ser mayor a cero.")

    return number


def list_suppliers() -> list[dict[str, Any]]:
    suppliers = load_suppliers()
    return sorted(suppliers, key=lambda supplier: supplier.get("nombre", "").lower())


def create_supplier(payload: dict[str, Any]) -> dict[str, Any]:
    suppliers = load_suppliers()

    supplier = {
        "id": next_record_id(suppliers),
        "nombre": _clean_text(payload.get("nombre"), "nombre"),
        "sector": _clean_text(payload.get("sector"), "sector"),
        "contacto": _clean_text(payload.get("contacto"), "contacto"),
    }

    suppliers.append(supplier)
    write_json_file(SUPPLIERS_FILE, suppliers)
    return supplier


def list_purchases(reference_date: date | None = None) -> list[dict[str, Any]]:
    today = reference_date or date.today()
    suppliers_map = {supplier["id"]: supplier for supplier in load_suppliers()}
    records: list[dict[str, Any]] = []

    for purchase in load_purchases():
        supplier = suppliers_map.get(purchase.get("proveedor_id"), {})
        remaining_days = calculate_remaining_days(
            purchase["fecha_compra"],
            int(purchase["dias_credito"]),
            reference_date=today,
        )
        records.append(
            {
                "id": purchase.get("id"),
                "factura": purchase.get("factura"),
                "proveedor_id": purchase.get("proveedor_id"),
                "proveedor": supplier.get("nombre", "Proveedor no encontrado"),
                "sku": purchase.get("sku"),
                "descripcion": purchase.get("descripcion"),
                "fecha_compra": purchase.get("fecha_compra"),
                "dias_credito": int(purchase.get("dias_credito", 0)),
                "monto_total": float(purchase.get("monto_total", 0) or 0),
                "remaining_days": remaining_days,
                "estado_credito": "Vencida" if remaining_days < 0 else "Vigente",
            }
        )

    records.sort(key=lambda purchase: purchase["fecha_compra"], reverse=True)
    return records


def create_purchase(payload: dict[str, Any]) -> dict[str, Any]:
    purchases = load_purchases()
    suppliers = {supplier["id"]: supplier for supplier in load_suppliers()}

    if not suppliers:
        raise ValueError("Primero debes registrar al menos un proveedor.")

    supplier_id = _clean_positive_int(payload.get("proveedor_id"), "proveedor_id")
    if supplier_id not in suppliers:
        raise ValueError("El proveedor seleccionado no existe.")

    purchase_date = _clean_text(payload.get("fecha_compra"), "fecha_compra")
    parse_date(purchase_date)

    purchase = {
        "id": next_record_id(purchases),
        "factura": _clean_text(payload.get("factura"), "factura"),
        "proveedor_id": supplier_id,
        "sku": _clean_text(payload.get("sku"), "sku"),
        "descripcion": _clean_text(payload.get("descripcion"), "descripcion"),
        "fecha_compra": purchase_date,
        "dias_credito": _clean_positive_int(payload.get("dias_credito"), "dias_credito"),
        "monto_total": _clean_positive_float(payload.get("monto_total"), "monto_total"),
    }

    purchases.append(purchase)
    write_json_file(PURCHASES_FILE, purchases)

    remaining_days = calculate_remaining_days(
        purchase["fecha_compra"],
        purchase["dias_credito"],
    )

    return {
        **purchase,
        "proveedor": suppliers[supplier_id]["nombre"],
        "remaining_days": remaining_days,
        "estado_credito": "Vencida" if remaining_days < 0 else "Vigente",
    }
