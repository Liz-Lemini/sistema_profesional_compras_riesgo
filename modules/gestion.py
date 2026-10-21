"""Operaciones de captura y consulta para compras y proveedores."""

from __future__ import annotations

from datetime import date
import re
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


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def _clean_optional_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_phone(value: Any, field_name: str = "telefono") -> str:
    phone = re.sub(r"\D", "", str(value or ""))
    if not 10 <= len(phone) <= 15:
        raise ValueError(f"El campo '{field_name}' debe contener entre 10 y 15 digitos.")
    return phone


def _clean_non_negative_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser entero.") from error

    if number < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")

    return number


def _clean_email(value: Any) -> str:
    email = _clean_optional_text(value)
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("El correo del proveedor no tiene un formato válido.")
    return email


def _supplier_email(supplier: dict[str, Any]) -> str:
    return _clean_optional_text(supplier.get("correo") or supplier.get("contacto"))


def _supplier_state(supplier: dict[str, Any]) -> str:
    return _clean_optional_text(supplier.get("estado")) or "Pendiente"


def _serialize_supplier(supplier: dict[str, Any]) -> dict[str, Any]:
    """Expone un proveedor con el esquema actual y compatibilidad con datos antiguos."""

    email = _supplier_email(supplier)
    return {
        "id": supplier.get("id"),
        "nombre": _clean_optional_text(supplier.get("nombre")),
        "asesor": _clean_optional_text(supplier.get("asesor")),
        "telefono": _clean_optional_text(supplier.get("telefono")),
        "correo": email,
        "contacto": email,
        "dias_credito": supplier.get("dias_credito"),
        "notas": _clean_optional_text(supplier.get("notas")),
        "sector": _clean_optional_text(supplier.get("sector")),
        "estado": _supplier_state(supplier),
        "fecha_registro": supplier.get("fecha_registro"),
    }


def _supplier_from_payload(
    payload: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    name = _clean_text(payload.get("nombre", current.get("nombre")), "nombre")
    advisor = _clean_text(payload.get("asesor", current.get("asesor")), "asesor")
    phone = _clean_phone(payload.get("telefono", current.get("telefono")))
    email = _clean_email(
        payload.get(
            "correo",
            payload.get("contacto", current.get("correo", current.get("contacto"))),
        )
    )
    credit_days = _clean_non_negative_int(
        payload.get("dias_credito", current.get("dias_credito")),
        "dias_credito",
    )
    notes = _clean_optional_text(payload.get("notas", current.get("notas")))
    sector = _clean_optional_text(payload.get("sector", current.get("sector")))

    return {
        **current,
        "nombre": name,
        "asesor": advisor,
        "telefono": phone,
        "correo": email,
        "dias_credito": credit_days,
        "notas": notes,
        "sector": sector,
    }


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


def _clean_non_negative_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser numerico.") from error

    if number < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")

    return round(number, 2)


PURCHASE_STATES = {"Emitida", "En proceso", "Confirmada", "Preparación", "En tránsito", "Parcial", "Recibida", "Cancelada"}


def _purchase_items(purchase: dict[str, Any]) -> list[dict[str, Any]]:
    items = purchase.get("items")
    if isinstance(items, list) and items:
        return items

    if purchase.get("sku") or purchase.get("descripcion"):
        return [
            {
                "sku": purchase.get("sku", ""),
                "descripcion": purchase.get("descripcion", ""),
                "cantidad": 1,
                "precio_unitario": round(float(purchase.get("monto_total", 0) or 0), 2),
            }
        ]

    return []


def _normalize_items(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    raw_items = payload.get("items")
    if raw_items is None and existing is not None:
        raw_items = existing.get("items")

    if raw_items is None:
        legacy_sku = payload.get("sku", existing.get("sku") if existing else None)
        legacy_description = payload.get(
            "descripcion",
            existing.get("descripcion") if existing else None,
        )
        legacy_amount = payload.get(
            "monto_total",
            existing.get("monto_total") if existing else None,
        )
        if legacy_sku or legacy_description:
            raw_items = [
                {
                    "sku": legacy_sku,
                    "descripcion": legacy_description,
                    "cantidad": 1,
                    "precio_unitario": legacy_amount,
                }
            ]

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("La orden debe contener al menos un producto.")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"La partida {index} no tiene un formato válido.")
        sku = _clean_text(item.get("sku"), f"sku de partida {index}")
        description = _clean_text(item.get("descripcion"), f"descripción de partida {index}")
        quantity = _clean_positive_int(item.get("cantidad"), f"cantidad de partida {index}")
        unit_price = _clean_positive_float(
            item.get("precio_unitario"),
            f"precio de partida {index}",
        )
        items.append(
            {
                "sku": sku,
                "descripcion": description,
                "cantidad": quantity,
                "precio_unitario": unit_price,
                "importe": round(quantity * unit_price, 2),
            }
        )

    return items


def _clean_optional_date(value: Any, field_name: str) -> str:
    text = _clean_optional_text(value)
    if not text:
        return ""
    try:
        parse_date(text)
    except ValueError as error:
        raise ValueError(f"El campo '{field_name}' debe tener formato AAAA-MM-DD.") from error
    return text


def _build_purchase(
    payload: dict[str, Any],
    purchases: list[dict[str, Any]],
    suppliers: dict[int, dict[str, Any]],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    supplier_id = _clean_positive_int(
        payload.get("proveedor_id", current.get("proveedor_id")),
        "proveedor_id",
    )
    if supplier_id not in suppliers:
        raise ValueError("El proveedor seleccionado no existe.")
    if suppliers[supplier_id].get("estado") == "Inactivo":
        raise ValueError("El proveedor seleccionado está inactivo.")

    order_date = _clean_text(
        payload.get(
            "fecha_orden",
            payload.get("fecha_compra", current.get("fecha_orden", current.get("fecha_compra"))),
        ),
        "fecha_orden",
    )
    parsed_order_date = parse_date(order_date)
    if parsed_order_date > date.today():
        raise ValueError("La fecha de orden no puede estar en el futuro.")

    delivery_date = _clean_optional_date(
        payload.get("fecha_entrega", current.get("fecha_entrega")),
        "fecha_entrega",
    )
    if delivery_date and parse_date(delivery_date) < parsed_order_date:
        raise ValueError("La fecha de entrega no puede ser anterior a la fecha de orden.")

    invoice = _clean_optional_text(payload.get("factura", current.get("factura")))
    if invoice and any(
        record.get("id") != current.get("id")
        and _normalized(record.get("factura")) == _normalized(invoice)
        for record in purchases
    ):
        raise ValueError("La factura ya está registrada.")

    state = _clean_optional_text(payload.get("estado", current.get("estado"))) or "Emitida"
    if state not in PURCHASE_STATES:
        raise ValueError("El estado de la orden no es válido.")

    supplier_credit_days = suppliers[supplier_id].get("dias_credito")
    credit_days = _clean_non_negative_int(
        payload.get("dias_credito", current.get("dias_credito", supplier_credit_days)),
        "dias_credito",
    )
    items = _normalize_items(payload, existing=current if existing else None)
    subtotal = round(sum(item["importe"] for item in items), 2)
    taxes = _clean_non_negative_float(
        payload.get("impuestos", current.get("impuestos", 0)),
        "impuestos",
    )
    total = round(subtotal + taxes, 2)
    purchase_id = current.get("id") or next_record_id(purchases)
    order_number = _clean_optional_text(payload.get("numero_orden", current.get("numero_orden")))
    order_number = order_number or f"OC-{order_date[:4]}-{purchase_id:04d}"
    first_item = items[0]

    return {
        **current,
        "id": purchase_id,
        "numero_orden": order_number,
        "proceso_id": (
            _clean_positive_int(payload.get("proceso_id"), "proceso_id")
            if payload.get("proceso_id") not in (None, "")
            else current.get("proceso_id")
        ),
        "cotizacion_id": (
            _clean_positive_int(payload.get("cotizacion_id"), "cotizacion_id")
            if payload.get("cotizacion_id") not in (None, "")
            else current.get("cotizacion_id")
        ),
        "negociacion_id": (
            _clean_positive_int(payload.get("negociacion_id"), "negociacion_id")
            if payload.get("negociacion_id") not in (None, "")
            else current.get("negociacion_id")
        ),
        "factura": invoice,
        "proveedor_id": supplier_id,
        "items": items,
        "subtotal": subtotal,
        "impuestos": taxes,
        "total": total,
        "monto_total": total,
        "sku": first_item["sku"],
        "descripcion": first_item["descripcion"],
        "fecha_orden": order_date,
        "fecha_compra": order_date,
        "dias_credito": credit_days,
        "estado": state,
        "fecha_entrega": delivery_date,
        "observaciones": _clean_optional_text(
            payload.get("observaciones", current.get("observaciones"))
        ),
    }


def _serialize_purchase(
    purchase: dict[str, Any],
    supplier: dict[str, Any],
    reference_date: date,
) -> dict[str, Any]:
    order_date = purchase.get("fecha_orden") or purchase.get("fecha_compra")
    credit_days = int(purchase.get("dias_credito", 0) or 0)
    try:
        remaining_days = calculate_remaining_days(
            order_date,
            credit_days,
            reference_date=reference_date,
        )
        credit_status = "Vencida" if remaining_days < 0 else "Vigente"
    except (TypeError, ValueError):
        remaining_days = None
        credit_status = "Fecha inválida"

    items = _purchase_items(purchase)
    total = float(purchase.get("total", purchase.get("monto_total", 0)) or 0)
    subtotal = float(purchase.get("subtotal", total) or 0)
    taxes = float(purchase.get("impuestos", 0) or 0)

    return {
        "id": purchase.get("id"),
        "numero_orden": purchase.get("numero_orden") or purchase.get("factura") or "Sin orden",
        "factura": purchase.get("factura", ""),
        "proveedor_id": purchase.get("proveedor_id"),
        "proveedor": supplier.get("nombre", "Proveedor no encontrado"),
        "items": items,
        "sku": purchase.get("sku") or (items[0].get("sku") if items else ""),
        "descripcion": purchase.get("descripcion") or (items[0].get("descripcion") if items else ""),
        "fecha_orden": order_date,
        "fecha_compra": order_date,
        "dias_credito": credit_days,
        "fecha_entrega": purchase.get("fecha_entrega", ""),
        "estado": purchase.get("estado") or "Sin definir",
        "observaciones": purchase.get("observaciones", ""),
        "subtotal": round(subtotal, 2),
        "impuestos": round(taxes, 2),
        "total": round(total, 2),
        "monto_total": round(total, 2),
        "remaining_days": remaining_days,
        "dias_restantes": remaining_days,
        "estado_credito": credit_status,
    }


def list_suppliers(query: str = "", state: str = "") -> list[dict[str, Any]]:
    suppliers = load_suppliers()
    normalized_query = _normalized(query)
    normalized_state = _normalized(state)
    records = [_serialize_supplier(supplier) for supplier in suppliers]

    if normalized_query:
        records = [
            supplier
            for supplier in records
            if normalized_query in _normalized(supplier.get("nombre"))
            or normalized_query in _normalized(supplier.get("asesor"))
            or normalized_query in _normalized(supplier.get("correo"))
            or normalized_query in _normalized(supplier.get("telefono"))
        ]

    if normalized_state:
        records = [
            supplier
            for supplier in records
            if _normalized(supplier.get("estado")) == normalized_state
        ]

    return sorted(records, key=lambda supplier: supplier.get("nombre", "").lower())


def create_supplier(payload: dict[str, Any]) -> dict[str, Any]:
    suppliers = load_suppliers()
    supplier = _supplier_from_payload(payload)

    if any(
        _normalized(record.get("nombre")) == _normalized(supplier["nombre"])
        for record in suppliers
    ):
        raise ValueError("Ya existe un proveedor con ese nombre.")

    supplier.update({
        "id": next_record_id(suppliers),
        "estado": "Activo",
        "fecha_registro": date.today().isoformat(),
    })

    suppliers.append(supplier)
    write_json_file(SUPPLIERS_FILE, suppliers)
    return _serialize_supplier(supplier)


def update_supplier(supplier_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    suppliers = load_suppliers()
    supplier = next((record for record in suppliers if record.get("id") == supplier_id), None)
    if supplier is None:
        raise ValueError("El proveedor seleccionado no existe.")

    updated = _supplier_from_payload(payload, existing=supplier)
    if any(
        record.get("id") != supplier_id
        and _normalized(record.get("nombre")) == _normalized(updated["nombre"])
        for record in suppliers
    ):
        raise ValueError("Ya existe otro proveedor con ese nombre.")

    supplier.clear()
    supplier.update(updated)
    write_json_file(SUPPLIERS_FILE, suppliers)
    return _serialize_supplier(supplier)


def set_supplier_state(supplier_id: int, state: str) -> dict[str, Any]:
    normalized_state = _clean_text(state, "estado").capitalize()
    if normalized_state not in {"Activo", "Inactivo"}:
        raise ValueError("El estado debe ser Activo o Inactivo.")

    suppliers = load_suppliers()
    supplier = next((record for record in suppliers if record.get("id") == supplier_id), None)
    if supplier is None:
        raise ValueError("El proveedor seleccionado no existe.")

    if normalized_state == "Activo":
        _supplier_from_payload(supplier, existing=supplier)

    supplier["estado"] = normalized_state
    write_json_file(SUPPLIERS_FILE, suppliers)
    return _serialize_supplier(supplier)


def get_supplier_history(supplier_id: int) -> dict[str, Any]:
    """Concentra cotizaciones, órdenes, entregas, incidencias y crédito del proveedor."""

    suppliers = load_suppliers()
    supplier = next((item for item in suppliers if item.get("id") == supplier_id), None)
    if supplier is None:
        raise ValueError("El proveedor seleccionado no existe.")

    supplier_orders = [
        _serialize_purchase(item, supplier, date.today())
        for item in load_purchases()
        if item.get("proveedor_id") == supplier_id
    ]
    from .proceso import load_incidents, load_payments, load_processes, load_quotes, load_receipts

    process_ids = {item.get("id") for item in load_processes() if item.get("proveedor_id") == supplier_id}
    quotes = [item for item in load_quotes() if item.get("proveedor_id") == supplier_id or item.get("proceso_id") in process_ids]
    incidents = [item for item in load_incidents() if item.get("proveedor_id") == supplier_id or item.get("proceso_id") in process_ids]
    order_ids = {item.get("id") for item in load_purchases() if item.get("proveedor_id") == supplier_id}
    receipts = [item for item in load_receipts() if item.get("orden_id") in order_ids or item.get("proceso_id") in process_ids]
    payments = [item for item in load_payments() if item.get("proveedor_id") == supplier_id or item.get("orden_id") in order_ids or item.get("proceso_id") in process_ids]
    return {
        "proveedor": _serialize_supplier(supplier),
        "resumen": {
            "cotizaciones": len(quotes),
            "ordenes": len(supplier_orders),
            "recepciones": len(receipts),
            "incidencias": len(incidents),
            "pagos": len(payments),
            "monto_compras": round(sum(item.get("total", 0) for item in supplier_orders), 2),
        },
        "cotizaciones": quotes,
        "ordenes": supplier_orders,
        "recepciones": receipts,
        "incidencias": incidents,
        "pagos": payments,
    }


def list_purchases(
    reference_date: date | None = None,
    query: str = "",
    state: str = "",
    supplier_id: Any = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict[str, Any]]:
    today = reference_date or date.today()
    start = parse_date(start_date) if str(start_date or "").strip() else None
    end = parse_date(end_date) if str(end_date or "").strip() else None
    if start and end and start > end:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    suppliers_map = {supplier["id"]: supplier for supplier in load_suppliers()}
    records: list[dict[str, Any]] = []

    for purchase in load_purchases():
        supplier = suppliers_map.get(purchase.get("proveedor_id"), {})
        record = _serialize_purchase(purchase, supplier, today)
        normalized_query = _normalized(query)
        normalized_state = _normalized(state)
        if normalized_query and not any(
            normalized_query in _normalized(record.get(field))
            for field in ("numero_orden", "factura", "proveedor", "sku", "descripcion")
        ):
            continue
        if normalized_state and _normalized(record.get("estado")) != normalized_state:
            continue
        if supplier_id not in (None, "") and str(record.get("proveedor_id")) != str(supplier_id):
            continue
        try:
            purchase_date = parse_date(str(record.get("fecha_orden", "")))
        except ValueError:
            continue
        if start and purchase_date < start:
            continue
        if end and purchase_date > end:
            continue
        records.append(record)

    records.sort(key=lambda purchase: purchase.get("fecha_orden") or "", reverse=True)
    return records


def create_purchase(payload: dict[str, Any]) -> dict[str, Any]:
    purchases = load_purchases()
    suppliers = {supplier["id"]: supplier for supplier in load_suppliers()}

    if not suppliers:
        raise ValueError("Primero debes registrar al menos un proveedor.")

    supplier_id = _clean_positive_int(payload.get("proveedor_id"), "proveedor_id")
    if suppliers.get(supplier_id, {}).get("estado") != "Activo":
        raise ValueError("Completa y activa el proveedor antes de registrar una orden.")

    purchase = _build_purchase(payload, purchases, suppliers)

    purchases.append(purchase)
    write_json_file(PURCHASES_FILE, purchases)
    return _serialize_purchase(purchase, suppliers[supplier_id], date.today())


def update_purchase(purchase_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    purchases = load_purchases()
    suppliers = {supplier["id"]: supplier for supplier in load_suppliers()}
    purchase = next((record for record in purchases if record.get("id") == purchase_id), None)
    if purchase is None:
        raise ValueError("La orden seleccionada no existe.")

    updated = _build_purchase(payload, purchases, suppliers, existing=purchase)
    purchase.clear()
    purchase.update(updated)
    write_json_file(PURCHASES_FILE, purchases)
    return _serialize_purchase(purchase, suppliers[purchase["proveedor_id"]], date.today())


def set_purchase_state(purchase_id: int, state: str) -> dict[str, Any]:
    normalized_state = _clean_text(state, "estado")
    if normalized_state not in PURCHASE_STATES:
        raise ValueError("El estado de la orden no es válido.")

    purchases = load_purchases()
    suppliers = {supplier["id"]: supplier for supplier in load_suppliers()}
    purchase = next((record for record in purchases if record.get("id") == purchase_id), None)
    if purchase is None:
        raise ValueError("La orden seleccionada no existe.")

    previous_state = purchase.get("estado") or "Sin definir"
    purchase["estado"] = normalized_state
    write_json_file(PURCHASES_FILE, purchases)
    if purchase.get("proceso_id") is not None:
        from .proceso import _append_event

        _append_event(
            purchase["proceso_id"],
            "cambio_estado_orden",
            normalized_state,
            f"Orden {purchase.get('numero_orden', purchase_id)}: {previous_state} → {normalized_state}.",
            extra={"orden_id": purchase_id, "estado_anterior": previous_state, "estado_nuevo": normalized_state},
        )
    return _serialize_purchase(
        purchase,
        suppliers.get(purchase.get("proveedor_id"), {}),
        date.today(),
    )
