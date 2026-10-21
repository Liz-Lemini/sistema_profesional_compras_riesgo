"""Expedientes integrados del proceso de compra.

Este módulo concentra la relación entre una necesidad, sus cotizaciones, la
decisión de proveedor, la negociación y la orden de compra. Los registros
heredados de compras y proveedores se conservan y sólo las operaciones nuevas
usan las relaciones del expediente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .analisis import parse_date
from .storage import next_record_id, read_json_file, write_json_file


PROCESSES_FILE = "procesos_compra.json"
QUOTES_FILE = "cotizaciones.json"
NEGOTIATIONS_FILE = "negociaciones.json"
EVENTS_FILE = "seguimientos_compra.json"
INCIDENTS_FILE = "incidencias.json"
RECEIPTS_FILE = "recepciones.json"
PAYMENTS_FILE = "pagos.json"
PAYMENT_MOVEMENTS_FILE = "pagos_aplicados.json"

PROCESS_STATES = {
    "borrador",
    "pendiente_cotizacion",
    "cotizando",
    "evaluacion",
    "negociacion",
    "proveedor_seleccionado",
    "orden_emitida",
    "seguimiento",
    "recepcion_parcial",
    "recibido",
    "pendiente_pago",
    "completado",
    "cancelado",
}

PROCESS_PRIORITIES = {"Baja", "Media", "Alta", "Urgente"}

PROCESS_TRANSITIONS = {
    "borrador": {"pendiente_cotizacion", "cancelado"},
    "pendiente_cotizacion": {"cotizando", "cancelado"},
    "cotizando": {"evaluacion", "negociacion", "cancelado"},
    "evaluacion": {"negociacion", "proveedor_seleccionado", "cancelado"},
    "negociacion": {"proveedor_seleccionado", "orden_emitida", "cancelado"},
    "proveedor_seleccionado": {"negociacion", "orden_emitida", "cancelado"},
    "orden_emitida": {"seguimiento", "recepcion_parcial", "recibido", "cancelado"},
    "seguimiento": {"recepcion_parcial", "recibido", "cancelado"},
    "recepcion_parcial": {"seguimiento", "recibido", "cancelado"},
    "recibido": {"pendiente_pago", "completado"},
    "pendiente_pago": {"completado"},
    "completado": set(),
    "cancelado": set(),
}


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _clean_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"El campo '{field_name}' es obligatorio.")
    return text


def _optional_text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return _optional_text(value).casefold()


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"El campo '{field_name}' debe ser entero positivo.")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser entero positivo.") from error
    if number <= 0:
        raise ValueError(f"El campo '{field_name}' debe ser entero positivo.")
    return number


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"El campo '{field_name}' debe ser entero no negativo.")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser entero no negativo.") from error
    if number < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")
    return number


def _positive_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser numérico.") from error
    if number <= 0:
        raise ValueError(f"El campo '{field_name}' debe ser mayor que cero.")
    return round(number, 2)


def _non_negative_float(value: Any, field_name: str) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser numérico.") from error
    if number < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")
    return round(number, 2)


def _date_text(value: Any, field_name: str, required: bool = True) -> str:
    text = _optional_text(value)
    if not text and not required:
        return ""
    if not text:
        raise ValueError(f"El campo '{field_name}' es obligatorio.")
    try:
        parse_date(text)
    except ValueError as error:
        raise ValueError(f"El campo '{field_name}' debe tener formato AAAA-MM-DD.") from error
    return text


def _read(filename: str) -> list[dict[str, Any]]:
    data = read_json_file(filename, default_data=[])
    return data if isinstance(data, list) else []


def load_processes() -> list[dict[str, Any]]:
    return _read(PROCESSES_FILE)


def load_quotes() -> list[dict[str, Any]]:
    return _read(QUOTES_FILE)


def load_negotiations() -> list[dict[str, Any]]:
    return _read(NEGOTIATIONS_FILE)


def load_events() -> list[dict[str, Any]]:
    return _read(EVENTS_FILE)


def load_incidents() -> list[dict[str, Any]]:
    return _read(INCIDENTS_FILE)


def load_receipts() -> list[dict[str, Any]]:
    return _read(RECEIPTS_FILE)


def load_payments() -> list[dict[str, Any]]:
    return _read(PAYMENTS_FILE)


def load_payment_movements() -> list[dict[str, Any]]:
    return _read(PAYMENT_MOVEMENTS_FILE)


def _supplier_map() -> dict[int, dict[str, Any]]:
    from .analisis import load_suppliers

    return {int(item["id"]): item for item in load_suppliers() if item.get("id") is not None}


def _process_map() -> dict[int, dict[str, Any]]:
    return {int(item["id"]): item for item in load_processes() if item.get("id") is not None}


def _append_event(
    process_id: int,
    event_type: str,
    status: str,
    comment: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    events = load_events()
    event = {
        "id": next_record_id(events),
        "proceso_id": process_id,
        "fecha_hora": _now(),
        "tipo": event_type,
        "estado": status,
        "comentario": comment,
    }
    if extra:
        event.update(extra)
    events.append(event)
    write_json_file(EVENTS_FILE, events)
    return event


def _set_process_state(
    process: dict[str, Any],
    new_state: str,
    comment: str = "",
    force: bool = False,
) -> dict[str, Any]:
    if new_state not in PROCESS_STATES:
        raise ValueError("El estado del proceso no es válido.")
    if new_state == "completado" and not force:
        raise ValueError("El cierre debe pasar por la lista de verificación del expediente.")
    current_state = process.get("estado", "borrador")
    if current_state == new_state:
        return process
    if not force and new_state not in PROCESS_TRANSITIONS.get(current_state, set()):
        raise ValueError(f"No se puede pasar de '{current_state}' a '{new_state}'.")

    timestamp = _now()
    process["estado"] = new_state
    process["updated_at"] = timestamp
    process["status_changed_at"] = timestamp
    _append_event(process["id"], "cambio_estado", new_state, comment)
    return process


def create_process(payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    creation_date = _date_text(payload.get("fecha_creacion", date.today().isoformat()), "fecha_creacion")
    if parse_date(creation_date) > date.today():
        raise ValueError("La fecha de creación no puede ser futura.")
    need = _clean_text(payload.get("necesidad", payload.get("descripcion")), "necesidad")
    priority = str(payload.get("prioridad", "Media")).strip().title()
    if priority not in PROCESS_PRIORITIES:
        raise ValueError("La prioridad no es válida.")

    process_id = next_record_id(processes)
    timestamp = _now()
    process = {
        "id": process_id,
        "folio": f"PC-{creation_date[:4]}-{process_id:04d}",
        "fecha_creacion": creation_date,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status_changed_at": timestamp,
        "responsable": _optional_text(payload.get("responsable")),
        "necesidad": need,
        "descripcion": need,
        "cantidad": _non_negative_int(payload.get("cantidad", 0), "cantidad"),
        "motivo": _optional_text(payload.get("motivo")),
        "prioridad": priority,
        "estado": "pendiente_cotizacion",
        "observaciones": _optional_text(payload.get("observaciones")),
    }
    processes.append(process)
    write_json_file(PROCESSES_FILE, processes)
    _append_event(process_id, "creacion", process["estado"], "Necesidad registrada.")
    return process


def list_processes(
    query: str = "",
    state: str = "",
    priority: str = "",
    supplier_id: Any = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict[str, Any]]:
    processes = load_processes()
    suppliers = _supplier_map()
    quotes = load_quotes()
    orders = _read("compras.json")
    normalized_query = _normalized(query)
    normalized_state = _normalized(state)
    normalized_priority = _normalized(priority)
    normalized_supplier = str(supplier_id or "").strip()
    start = parse_date(start_date) if str(start_date or "").strip() else None
    end = parse_date(end_date) if str(end_date or "").strip() else None
    if start and end and start > end:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    result = []
    for process in processes:
        process_id = process.get("id")
        selected_provider = suppliers.get(process.get("proveedor_id"), {})
        record = {
            **process,
            "proveedor": selected_provider.get("nombre", ""),
            "cotizaciones_count": sum(item.get("proceso_id") == process_id for item in quotes),
            "ordenes_count": sum(item.get("proceso_id") == process_id for item in orders),
        }
        searchable = " ".join(
            str(record.get(field, ""))
            for field in ("folio", "necesidad", "descripcion", "proveedor", "responsable")
        )
        if normalized_query and normalized_query not in _normalized(searchable):
            continue
        if normalized_state and _normalized(record.get("estado")) != normalized_state:
            continue
        if normalized_priority and _normalized(record.get("prioridad")) != normalized_priority:
            continue
        if normalized_supplier and str(record.get("proveedor_id", "")) != normalized_supplier:
            continue
        try:
            process_date = parse_date(str(record.get("fecha_creacion", "")))
        except ValueError:
            process_date = None
        if start and (process_date is None or process_date < start):
            continue
        if end and (process_date is None or process_date > end):
            continue
        result.append(record)
    return sorted(result, key=lambda item: item.get("updated_at", ""), reverse=True)


def get_process(process_id: int) -> dict[str, Any]:
    process = next((item for item in load_processes() if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")

    suppliers = _supplier_map()
    quotes = [item for item in load_quotes() if item.get("proceso_id") == process_id]
    for quote in quotes:
        quote["proveedor"] = suppliers.get(quote.get("proveedor_id"), {}).get("nombre", "Proveedor no encontrado")
    negotiations = [item for item in load_negotiations() if item.get("proceso_id") == process_id]
    events = sorted(
        (item for item in load_events() if item.get("proceso_id") == process_id),
        key=lambda item: (item.get("created_at", ""), str(item.get("id", ""))),
    )
    incidents = [item for item in load_incidents() if item.get("proceso_id") == process_id]
    receptions = [item for item in load_receipts() if item.get("proceso_id") == process_id]
    payments = [item for item in load_payments() if item.get("proceso_id") == process_id]
    payment_movements = [
        item for item in load_payment_movements()
        if any(payment.get("id") == item.get("pago_id") for payment in payments)
    ]

    from .gestion import _serialize_purchase

    orders = []
    for order in _read("compras.json"):
        if order.get("proceso_id") != process_id:
            continue
        supplier = suppliers.get(order.get("proveedor_id"), {})
        orders.append(_serialize_purchase(order, supplier, date.today()))

    return {
        **process,
        "proveedor": suppliers.get(process.get("proveedor_id"), {}).get("nombre", ""),
        "cotizaciones": quotes,
        "negociaciones": negotiations,
        "ordenes": orders,
        "seguimiento": events,
        "incidencias": incidents,
        "recepciones": receptions,
        "pagos": payments,
        "resumen": {
            "cotizaciones": len(quotes),
            "negociaciones": len(negotiations),
            "ordenes": len(orders),
            "eventos": len(events),
            "incidencias": len(incidents),
            "recepciones": len(receptions),
            "pagos": len(payments),
            "movimientos_pago": len(payment_movements),
        },
        "pagos_aplicados": payment_movements,
        "cierre": closure_checklist(process_id, process.get("pago_aplica", True)),
    }


def update_process(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")

    if "necesidad" in payload or "descripcion" in payload:
        need = _clean_text(payload.get("necesidad", payload.get("descripcion")), "necesidad")
        process["necesidad"] = need
        process["descripcion"] = need
    if "cantidad" in payload:
        process["cantidad"] = _non_negative_int(payload.get("cantidad"), "cantidad")
    if "prioridad" in payload:
        priority = str(payload.get("prioridad")).strip().title()
        if priority not in PROCESS_PRIORITIES:
            raise ValueError("La prioridad no es válida.")
        process["prioridad"] = priority
    for field in ("responsable", "motivo", "observaciones"):
        if field in payload:
            process[field] = _optional_text(payload.get(field))
    if "estado" in payload:
        _set_process_state(process, _optional_text(payload.get("estado")), _optional_text(payload.get("comentario")))
    process["updated_at"] = _now()
    write_json_file(PROCESSES_FILE, processes)
    return process


def set_process_state(process_id: int, state: str, comment: str = "") -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    _set_process_state(process, _clean_text(state, "estado"), _optional_text(comment))
    write_json_file(PROCESSES_FILE, processes)
    return process


def add_quote(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    if process.get("estado") in {"completado", "cancelado"}:
        raise ValueError("No se pueden agregar cotizaciones a un proceso cerrado.")

    suppliers = _supplier_map()
    supplier_id = _positive_int(payload.get("proveedor_id"), "proveedor_id")
    supplier = suppliers.get(supplier_id)
    if supplier is None:
        raise ValueError("El proveedor seleccionado no existe.")
    if (supplier.get("estado") or "Pendiente") != "Activo":
        raise ValueError("Completa y activa el proveedor antes de agregar una cotización.")

    quantity = _positive_int(payload.get("cantidad"), "cantidad")
    unit_price = _positive_float(payload.get("precio_unitario"), "precio_unitario")
    shipping = _non_negative_float(payload.get("envio", 0), "envio")
    taxes = _non_negative_float(payload.get("impuestos", 0), "impuestos")
    quote_date = _date_text(payload.get("fecha", date.today().isoformat()), "fecha")
    if parse_date(quote_date) > date.today():
        raise ValueError("La fecha de cotización no puede ser futura.")
    validity = _date_text(payload.get("vigencia"), "vigencia", required=False)
    if validity and parse_date(validity) < parse_date(quote_date):
        raise ValueError("La vigencia no puede ser anterior a la fecha de cotización.")
    availability = _optional_text(payload.get("disponibilidad"))
    if availability and availability not in {"Disponible", "Parcial", "No disponible"}:
        raise ValueError("La disponibilidad no es válida.")

    quotes = load_quotes()
    quote_id = next_record_id(quotes)
    subtotal = round(quantity * unit_price, 2)
    quote = {
        "id": quote_id,
        "folio": f"COT-{quote_date[:4]}-{quote_id:04d}",
        "proceso_id": process_id,
        "proveedor_id": supplier_id,
        "sku": _clean_text(payload.get("sku"), "sku"),
        "descripcion": _clean_text(payload.get("descripcion"), "descripcion"),
        "cantidad": quantity,
        "precio_unitario": unit_price,
        "subtotal": subtotal,
        "envio": shipping,
        "impuestos": taxes,
        "costo_total": round(subtotal + shipping + taxes, 2),
        "dias_credito": _non_negative_int(payload.get("dias_credito", supplier.get("dias_credito", 0)), "dias_credito"),
        "plazo_entrega_dias": _non_negative_int(payload.get("plazo_entrega_dias", 0), "plazo_entrega_dias"),
        "fecha": quote_date,
        "vigencia": validity,
        "disponibilidad": availability,
        "observaciones": _optional_text(payload.get("observaciones")),
        "seleccionada": False,
        "created_at": _now(),
    }
    quotes.append(quote)
    write_json_file(QUOTES_FILE, quotes)
    if process.get("estado") in {"borrador", "pendiente_cotizacion"}:
        _set_process_state(process, "cotizando", "Se agregó una cotización.")
    process["updated_at"] = _now()
    write_json_file(PROCESSES_FILE, processes)
    return {**quote, "proveedor": supplier.get("nombre", "")}


def compare_quotes(process_id: int) -> dict[str, Any]:
    suppliers = _supplier_map()
    quotes = [item for item in load_quotes() if item.get("proceso_id") == process_id]
    if not quotes:
        return {"cotizaciones": [], "destacados": {}}
    rows = []
    for quote in quotes:
        rows.append({
            **quote,
            "proveedor": suppliers.get(quote.get("proveedor_id"), {}).get("nombre", "Proveedor no encontrado"),
        })
    return {
        "cotizaciones": rows,
        "destacados": {
            "menor_costo_total": min(rows, key=lambda item: item["costo_total"])["id"],
            "mayor_credito": max(rows, key=lambda item: item["dias_credito"])["id"],
            "menor_plazo_entrega": min(rows, key=lambda item: item["plazo_entrega_dias"])["id"],
        },
    }


def select_quote(process_id: int, quote_id: int, justification: str) -> dict[str, Any]:
    justification = _clean_text(justification, "justificación")
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    quotes = load_quotes()
    selected = next(
        (item for item in quotes if item.get("id") == quote_id and item.get("proceso_id") == process_id),
        None,
    )
    if selected is None:
        raise ValueError("La cotización seleccionada no pertenece al proceso.")
    for quote in quotes:
        if quote.get("proceso_id") == process_id:
            quote["seleccionada"] = quote.get("id") == quote_id
    process["cotizacion_seleccionada_id"] = quote_id
    process["proveedor_id"] = selected.get("proveedor_id")
    process["justificacion_seleccion"] = justification
    _set_process_state(process, "proveedor_seleccionado", "Proveedor seleccionado con justificación.", force=True)
    write_json_file(QUOTES_FILE, quotes)
    write_json_file(PROCESSES_FILE, processes)
    return selected


def add_negotiation(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    quote_id = _positive_int(payload.get("cotizacion_id", process.get("cotizacion_seleccionada_id")), "cotizacion_id")
    quote = next((item for item in load_quotes() if item.get("id") == quote_id and item.get("proceso_id") == process_id), None)
    if quote is None:
        raise ValueError("La cotización no pertenece al proceso.")

    original_price = _positive_float(payload.get("precio_cotizado", quote.get("precio_unitario")), "precio_cotizado")
    final_price = _positive_float(payload.get("precio_negociado"), "precio_negociado")
    original_credit = _non_negative_int(payload.get("credito_original", quote.get("dias_credito", 0)), "credito_original")
    final_credit = _non_negative_int(payload.get("credito_negociado", original_credit), "credito_negociado")
    original_delivery = _non_negative_int(payload.get("plazo_original", quote.get("plazo_entrega_dias", 0)), "plazo_original")
    final_delivery = _non_negative_int(payload.get("plazo_negociado", original_delivery), "plazo_negociado")
    quantity = int(quote.get("cantidad", 0))
    savings_unit = round(original_price - final_price, 2)
    negotiation = {
        "id": next_record_id(load_negotiations()),
        "proceso_id": process_id,
        "cotizacion_id": quote_id,
        "precio_cotizado": original_price,
        "precio_negociado": final_price,
        "credito_original": original_credit,
        "credito_negociado": final_credit,
        "plazo_original": original_delivery,
        "plazo_negociado": final_delivery,
        "ahorro_unitario": savings_unit,
        "ahorro_total": round(savings_unit * quantity, 2),
        "condiciones_adicionales": _optional_text(payload.get("condiciones_adicionales")),
        "fecha": _date_text(payload.get("fecha", date.today().isoformat()), "fecha"),
        "observaciones": _optional_text(payload.get("observaciones")),
        "created_at": _now(),
    }
    negotiations = load_negotiations()
    negotiations.append(negotiation)
    write_json_file(NEGOTIATIONS_FILE, negotiations)
    if process.get("estado") != "negociacion":
        _set_process_state(process, "negociacion", "Se registró una negociación.", force=True)
    write_json_file(PROCESSES_FILE, processes)
    return negotiation


def create_order_from_process(process_id: int) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    if process.get("estado") in {"borrador", "pendiente_cotizacion", "cotizando", "evaluacion", "cancelado", "completado"}:
        raise ValueError("El proceso todavía no está listo para generar una orden.")
    if process.get("orden_id") not in (None, ""):
        raise ValueError("El proceso ya tiene una orden de compra vinculada.")

    quote_id = process.get("cotizacion_seleccionada_id")
    quote = next((item for item in load_quotes() if item.get("id") == quote_id and item.get("proceso_id") == process_id), None)
    if quote is None:
        raise ValueError("Selecciona una cotización antes de generar la orden.")
    if process.get("proveedor_id") is None:
        raise ValueError("El proceso no tiene proveedor seleccionado.")

    latest_negotiation = next(
        (item for item in reversed(load_negotiations()) if item.get("proceso_id") == process_id and item.get("cotizacion_id") == quote_id),
        None,
    )
    price = latest_negotiation.get("precio_negociado") if latest_negotiation else quote["precio_unitario"]
    credit = latest_negotiation.get("credito_negociado") if latest_negotiation else quote["dias_credito"]
    delivery_days = latest_negotiation.get("plazo_negociado") if latest_negotiation else quote.get("plazo_entrega_dias", 0)
    delivery_date = (date.today() + timedelta(days=delivery_days)).isoformat() if delivery_days else ""

    from .gestion import create_purchase

    order = create_purchase({
        "proceso_id": process_id,
        "cotizacion_id": quote_id,
        "negociacion_id": latest_negotiation.get("id") if latest_negotiation else None,
        "proveedor_id": process["proveedor_id"],
        "fecha_orden": date.today().isoformat(),
        "dias_credito": credit,
        "items": [{
            "sku": quote["sku"],
            "descripcion": quote["descripcion"],
            "cantidad": quote["cantidad"],
            "precio_unitario": price,
        }],
        "impuestos": quote.get("impuestos", 0),
        "fecha_entrega": delivery_date,
        "estado": "Emitida",
        "observaciones": f"Generada desde {process['folio']}.",
    })
    for record in processes:
        if record.get("id") == process_id:
            record["orden_id"] = order["id"]
            _set_process_state(record, "orden_emitida", "Orden de compra generada.", force=True)
            break
    write_json_file(PROCESSES_FILE, processes)
    return order


FOLLOWUP_TYPES = {"confirmacion", "en_transito", "actualizacion", "recepcion", "otro"}
INCIDENT_TYPES = {
    "retraso",
    "producto_danado",
    "cantidad_incorrecta",
    "producto_incorrecto",
    "diferencia_precio",
    "faltante",
    "documentacion",
    "otro",
}
INCIDENT_STATES = {"abierta", "en_revision", "resuelta", "cancelada"}


def add_followup(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")

    event_type = _optional_text(payload.get("tipo")) or "actualizacion"
    if event_type not in FOLLOWUP_TYPES:
        raise ValueError("El tipo de seguimiento no es válido.")
    order_id = payload.get("orden_id")
    if order_id not in (None, ""):
        order_id = _positive_int(order_id, "orden_id")
        _process_order(process_id, order_id)
    estimated = _date_text(payload.get("fecha_estimada"), "fecha_estimada", required=False)
    actual = _date_text(payload.get("fecha_real"), "fecha_real", required=False)
    deviation = None
    if estimated and actual:
        deviation = (parse_date(actual) - parse_date(estimated)).days

    if process.get("estado") == "orden_emitida":
        _set_process_state(process, "seguimiento", "Se agregó un evento de seguimiento.", force=True)
    event = _append_event(
        process_id,
        event_type,
        _optional_text(payload.get("estado")),
        _optional_text(payload.get("comentario")),
        extra={
            "orden_id": order_id,
            "fecha_estimada": estimated,
            "fecha_real": actual,
            "desviacion_dias": deviation,
            "retrasado": deviation is not None and deviation > 0,
        },
    )
    write_json_file(PROCESSES_FILE, processes)
    return event


def add_incident(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")

    incident_type = _clean_text(payload.get("tipo"), "tipo")
    if incident_type not in INCIDENT_TYPES:
        raise ValueError("El tipo de incidencia no es válido.")
    incident_date = _date_text(payload.get("fecha", date.today().isoformat()), "fecha")
    if parse_date(incident_date) > date.today():
        raise ValueError("La fecha de la incidencia no puede ser futura.")
    order_id = payload.get("orden_id")
    if order_id not in (None, ""):
        order_id = _positive_int(order_id, "orden_id")
        _process_order(process_id, order_id)
    provider_id = payload.get("proveedor_id", process.get("proveedor_id"))
    if provider_id not in (None, ""):
        provider_id = _positive_int(provider_id, "proveedor_id")

    incidents = load_incidents()
    incident = {
        "id": next_record_id(incidents),
        "folio": f"INC-{incident_date[:4]}-{next_record_id(incidents):04d}",
        "proceso_id": process_id,
        "orden_id": order_id,
        "proveedor_id": provider_id,
        "sku": _optional_text(payload.get("sku")),
        "fecha": incident_date,
        "tipo": incident_type,
        "descripcion": _clean_text(payload.get("descripcion"), "descripcion"),
        "estado": _optional_text(payload.get("estado")) or "abierta",
        "resolucion": _optional_text(payload.get("resolucion")),
        "fecha_resolucion": _date_text(payload.get("fecha_resolucion"), "fecha_resolucion", required=False),
        "created_at": _now(),
        "updated_at": _now(),
    }
    if incident["estado"] not in INCIDENT_STATES:
        raise ValueError("El estado de la incidencia no es válido.")
    incidents.append(incident)
    write_json_file(INCIDENTS_FILE, incidents)
    _append_event(process_id, "incidencia", process.get("estado", ""), incident["descripcion"], {"incidencia_id": incident["id"]})
    return incident


def update_incident(incident_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Actualiza el estado y la resolución de una incidencia registrada."""

    incidents = load_incidents()
    incident = next((item for item in incidents if item.get("id") == incident_id), None)
    if incident is None:
        raise ValueError("La incidencia seleccionada no existe.")

    state = _clean_text(payload.get("estado"), "estado").casefold()
    if state not in INCIDENT_STATES:
        raise ValueError("El estado de la incidencia no es válido.")
    incident["estado"] = state
    incident["resolucion"] = _optional_text(payload.get("resolucion", incident.get("resolucion")))
    resolution_date = (
        date.today().isoformat()
        if state == "resuelta"
        else _date_text(payload.get("fecha_resolucion", incident.get("fecha_resolucion")), "fecha_resolucion", required=False)
    )
    if resolution_date and parse_date(resolution_date) > date.today():
        raise ValueError("La fecha de resolución no puede ser futura.")
    incident["fecha_resolucion"] = resolution_date
    incident["updated_at"] = _now()
    write_json_file(INCIDENTS_FILE, incidents)

    process_id = incident.get("proceso_id")
    if process_id is not None:
        _append_event(
            process_id,
            "incidencia_actualizada",
            state,
            incident["resolucion"] or incident.get("descripcion", ""),
            {"incidencia_id": incident_id},
        )
    return incident


def _process_order(process_id: int, order_id: int) -> dict[str, Any]:
    order = next(
        (
            item for item in _read("compras.json")
            if item.get("id") == order_id and item.get("proceso_id") == process_id
        ),
        None,
    )
    if order is None:
        raise ValueError("La orden no existe o no pertenece al proceso.")
    return order


def add_reception(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    order_id = _positive_int(payload.get("orden_id"), "orden_id")
    order = _process_order(process_id, order_id)
    ordered_items = {
        item.get("sku"): _positive_int(item.get("cantidad"), "cantidad solicitada")
        for item in order.get("items", [])
    }
    if not ordered_items:
        raise ValueError("La orden no tiene partidas para recibir.")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("La recepción debe contener al menos una partida.")

    previous_received: dict[str, int] = {}
    for previous in load_receipts():
        if previous.get("orden_id") != order_id:
            continue
        for item in previous.get("items", []):
            previous_received[item.get("sku")] = previous_received.get(item.get("sku"), 0) + int(item.get("cantidad_recibida", 0) or 0)

    normalized_items = []
    accepted_total = 0
    rejected_total = 0
    received_skus = set()
    for item in items:
        sku = _clean_text(item.get("sku"), "sku de recepción")
        if sku not in ordered_items:
            raise ValueError(f"El SKU '{sku}' no pertenece a la orden.")
        if sku in received_skus:
            raise ValueError(f"El SKU '{sku}' aparece más de una vez en la recepción.")
        received_skus.add(sku)
        received = _non_negative_int(item.get("cantidad_recibida"), "cantidad_recibida")
        accepted = _non_negative_int(item.get("cantidad_aceptada", received), "cantidad_aceptada")
        rejected = _non_negative_int(item.get("cantidad_rechazada", 0), "cantidad_rechazada")
        if accepted + rejected != received:
            raise ValueError("La cantidad aceptada más rechazada debe coincidir con la recibida.")
        if previous_received.get(sku, 0) + received > ordered_items[sku]:
            raise ValueError(f"La recepción del SKU '{sku}' supera la cantidad solicitada.")
        normalized_items.append({
            "sku": sku,
            "cantidad_solicitada": ordered_items[sku],
            "cantidad_recibida": received,
            "cantidad_aceptada": accepted,
            "cantidad_rechazada": rejected,
        })
        accepted_total += accepted
        rejected_total += rejected

    receipts = load_receipts()
    reception_id = next_record_id(receipts)
    reception_date = _date_text(payload.get("fecha", date.today().isoformat()), "fecha")
    if parse_date(reception_date) > date.today():
        raise ValueError("La fecha de recepción no puede ser futura.")
    cumulative = dict(previous_received)
    for item in normalized_items:
        cumulative[item["sku"]] = cumulative.get(item["sku"], 0) + item["cantidad_recibida"]
    complete = all(cumulative.get(sku, 0) >= quantity for sku, quantity in ordered_items.items())
    from .inventario import load_inventory

    inventory_skus = {
        str(item.get("sku", "")).strip().casefold()
        for item in load_inventory()
    }
    missing_inventory_skus = [
        item["sku"] for item in normalized_items
        if item["cantidad_aceptada"] > 0 and item["sku"].casefold() not in inventory_skus
    ]
    if missing_inventory_skus:
        raise ValueError(
            "No se puede registrar la recepción: SKU(s) sin artículo en inventario: "
            + ", ".join(missing_inventory_skus)
            + "."
        )
    reception = {
        "id": reception_id,
        "folio": f"REC-{reception_date[:4]}-{reception_id:04d}",
        "proceso_id": process_id,
        "orden_id": order_id,
        "fecha": reception_date,
        "items": normalized_items,
        "estado": "recibido" if complete else "recepcion_parcial",
        "total_aceptado": accepted_total,
        "total_rechazado": rejected_total,
        "observaciones": _optional_text(payload.get("observaciones")),
        "created_at": _now(),
    }
    receipts.append(reception)
    write_json_file(RECEIPTS_FILE, receipts)

    from .inventario import create_inventory_movement

    inventory_movements = []
    for item in normalized_items:
        if item["cantidad_aceptada"] <= 0:
            continue
        inventory_movements.append(create_inventory_movement({
            "sku": item["sku"],
            "tipo": "Entrada",
            "cantidad": item["cantidad_aceptada"],
            "fecha": reception_date,
            "origen_tipo": "recepcion",
            "origen_id": reception_id,
            "referencia": reception["folio"],
            "proceso_id": process_id,
            "orden_id": order_id,
            "observaciones": f"Entrada automática por {reception['folio']}.",
        }))

    next_state = "recibido" if complete else "recepcion_parcial"
    _set_process_state(process, next_state, f"Recepción {reception['folio']} registrada.", force=True)
    write_json_file(PROCESSES_FILE, processes)
    suggested_incident = None
    if rejected_total:
        suggested_incident = add_incident(process_id, {
            "orden_id": order_id,
            "tipo": "cantidad_incorrecta",
            "fecha": reception_date,
            "descripcion": f"Se rechazaron {rejected_total} unidades en {reception['folio']}.",
        })
    return {**reception, "movimientos_inventario": inventory_movements, "incidencia_sugerida": suggested_incident}


def closure_checklist(process_id: int, payment_applies: bool = True) -> dict[str, Any]:
    """Evalúa requisitos explícitos antes de marcar un expediente como completado."""

    process = next((item for item in load_processes() if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    order = None
    if process.get("orden_id") not in (None, ""):
        order = next((item for item in _read("compras.json") if item.get("id") == process.get("orden_id")), None)
        if order and order.get("proceso_id") != process_id:
            order = None
    receipts = [item for item in load_receipts() if item.get("proceso_id") == process_id]
    incidents = [item for item in load_incidents() if item.get("proceso_id") == process_id]
    payments = [item for item in load_payments() if item.get("proceso_id") == process_id]
    checks = [
        {
            "clave": "proveedor",
            "nombre": "Proveedor seleccionado",
            "cumple": process.get("proveedor_id") not in (None, "") and process.get("cotizacion_seleccionada_id") not in (None, ""),
            "detalle": "Existe una cotización seleccionada." if process.get("cotizacion_seleccionada_id") not in (None, "") else "Falta seleccionar una cotización.",
        },
        {
            "clave": "orden",
            "nombre": "Orden vinculada",
            "cumple": order is not None,
            "detalle": "La orden está vinculada al expediente." if order else "Falta generar una orden.",
        },
        {
            "clave": "recepcion",
            "nombre": "Recepción completa",
            "cumple": any(item.get("estado") == "recibido" for item in receipts),
            "detalle": "Existe una recepción completa." if any(item.get("estado") == "recibido" for item in receipts) else "La recepción está pendiente o es parcial.",
        },
        {
            "clave": "incidencias",
            "nombre": "Incidencias resueltas o justificadas",
            "cumple": all(item.get("estado") in {"resuelta", "cancelada"} or _optional_text(item.get("resolucion")) for item in incidents),
            "detalle": "No hay incidencias abiertas sin resolución." if all(item.get("estado") in {"resuelta", "cancelada"} or _optional_text(item.get("resolucion")) for item in incidents) else "Hay incidencias abiertas sin resolución o justificación.",
        },
        {
            "clave": "pago",
            "nombre": "Pago definido",
            "cumple": not payment_applies or bool(payments),
            "detalle": "Pago no aplica al expediente." if not payment_applies else ("Existe al menos una obligación de pago registrada." if payments else "Registra una obligación de pago o indica que no aplica."),
        },
    ]
    return {"puede_cerrar": all(item["cumple"] for item in checks), "pago_aplica": payment_applies, "validaciones": checks}


def close_process(process_id: int, payment_applies: bool = True) -> dict[str, Any]:
    checklist = closure_checklist(process_id, payment_applies)
    if not checklist["puede_cerrar"]:
        missing = ", ".join(item["nombre"] for item in checklist["validaciones"] if not item["cumple"])
        raise ValueError(f"No se puede cerrar el expediente. Falta: {missing}.")
    processes = load_processes()
    process = next(item for item in processes if item.get("id") == process_id)
    process["pago_aplica"] = bool(payment_applies)
    process["closed_at"] = _now()
    _set_process_state(process, "completado", "Expediente cerrado con lista de verificación aprobada.", force=True)
    write_json_file(PROCESSES_FILE, processes)
    return process


def _payment_status(amount: float, paid: float, due_date: str, reference_date: date | None = None) -> str:
    if paid >= amount:
        return "pagado"
    if paid > 0:
        return "parcial"
    if parse_date(due_date) < (reference_date or date.today()):
        return "vencido"
    return "pendiente"


def create_payment_obligation(process_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    processes = load_processes()
    process = next((item for item in processes if item.get("id") == process_id), None)
    if process is None:
        raise ValueError("El proceso de compra no existe.")
    order_id = _positive_int(payload.get("orden_id"), "orden_id")
    order = _process_order(process_id, order_id)
    invoice_date = _date_text(payload.get("fecha_factura", date.today().isoformat()), "fecha_factura")
    credit_days = _non_negative_int(payload.get("dias_credito", order.get("dias_credito", 0)), "dias_credito")
    due_date = (parse_date(invoice_date) + timedelta(days=credit_days)).isoformat()
    amount = _positive_float(payload.get("monto", order.get("total", order.get("monto_total"))), "monto")
    payments = load_payments()
    invoice = _optional_text(payload.get("factura"))
    if invoice and any(_normalized(item.get("factura")) == _normalized(invoice) for item in payments):
        raise ValueError("La factura ya tiene una obligación de pago registrada.")
    payment_id = next_record_id(payments)
    payment = {
        "id": payment_id,
        "folio": f"PAG-{invoice_date[:4]}-{payment_id:04d}",
        "proceso_id": process_id,
        "orden_id": order_id,
        "proveedor_id": order.get("proveedor_id"),
        "factura": invoice,
        "monto": amount,
        "fecha_factura": invoice_date,
        "dias_credito": credit_days,
        "fecha_vencimiento": due_date,
        "monto_pagado": 0.0,
        "saldo": amount,
        "estado": _payment_status(amount, 0, due_date),
        "observaciones": _optional_text(payload.get("observaciones")),
        "created_at": _now(),
        "updated_at": _now(),
    }
    payments.append(payment)
    write_json_file(PAYMENTS_FILE, payments)
    if process.get("estado") == "recibido":
        _set_process_state(process, "pendiente_pago", "Se registró una obligación de pago.", force=True)
    write_json_file(PROCESSES_FILE, processes)
    return payment


def register_payment(payment_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    payments = load_payments()
    payment = next((item for item in payments if item.get("id") == payment_id), None)
    if payment is None:
        raise ValueError("La obligación de pago no existe.")
    amount = _positive_float(payload.get("monto"), "monto")
    balance = round(float(payment.get("saldo", payment.get("monto", 0)) or 0), 2)
    if amount > balance:
        raise ValueError("El pago no puede superar el saldo pendiente.")
    payment_date = _date_text(payload.get("fecha", date.today().isoformat()), "fecha")
    if parse_date(payment_date) > date.today():
        raise ValueError("La fecha del pago no puede ser futura.")
    movements = load_payment_movements()
    movement = {
        "id": next_record_id(movements),
        "pago_id": payment_id,
        "fecha": payment_date,
        "monto": amount,
        "observaciones": _optional_text(payload.get("observaciones")),
        "created_at": _now(),
    }
    movements.append(movement)
    payment["monto_pagado"] = round(float(payment.get("monto_pagado", 0) or 0) + amount, 2)
    payment["saldo"] = round(float(payment.get("monto", 0) or 0) - payment["monto_pagado"], 2)
    payment["estado"] = _payment_status(float(payment["monto"]), payment["monto_pagado"], payment["fecha_vencimiento"])
    payment["updated_at"] = _now()
    write_json_file(PAYMENT_MOVEMENTS_FILE, movements)
    write_json_file(PAYMENTS_FILE, payments)

    processes = load_processes()
    process = next((item for item in processes if item.get("id") == payment.get("proceso_id")), None)
    if process:
        process_payments = [item for item in payments if item.get("proceso_id") == payment.get("proceso_id")]
        target_state = "pendiente_pago" if process_payments else "recibido"
        _set_process_state(process, target_state, f"Pago aplicado por {amount:.2f}.", force=True)
        write_json_file(PROCESSES_FILE, processes)
    return {"pago": payment, "movimiento": movement}
