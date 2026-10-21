"""Validaciones de calidad e integridad para los datos operativos."""

from __future__ import annotations

from datetime import date
from math import isclose, isfinite
import re
from typing import Any

from .analisis import PURCHASES_FILE, SUPPLIERS_FILE, parse_date
from .inventario import INVENTORY_FILE, MOVEMENTS_FILE, MOVEMENT_TYPES
from .proceso import (
    EVENTS_FILE,
    INCIDENTS_FILE,
    INCIDENT_STATES,
    NEGOTIATIONS_FILE,
    PAYMENT_MOVEMENTS_FILE,
    PAYMENTS_FILE,
    PROCESS_PRIORITIES,
    PROCESS_STATES,
    PROCESSES_FILE,
    QUOTES_FILE,
    RECEIPTS_FILE,
)
from .storage import StorageError, read_json_file


INVENTORY_REQUIRED_FIELDS = (
    "sku",
    "descripcion",
    "stock_actual",
    "stock_minimo",
    "valor_unitario",
    "dias_sin_movimiento",
)

PURCHASE_STATES = {"Emitida", "En proceso", "Parcial", "Recibida", "Cancelada"}


def _is_positive_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number > 0


def _is_non_negative_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number >= 0


def _is_positive_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number.is_integer() and number > 0


def _is_non_negative_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number.is_integer() and number >= 0


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_phone(value: Any) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    return 10 <= len(digits) <= 15


def _key(value: Any) -> Any:
    """Convierte valores no hashables en una clave segura para detectar duplicados."""
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def _record_reference(record: dict[str, Any]) -> dict[str, Any]:
    """Expone una referencia breve para que QA sea accionable."""

    reference = (
        record.get("nombre")
        or record.get("factura")
        or record.get("numero_orden")
        or record.get("sku")
        or record.get("id")
        or "Registro sin referencia"
    )
    return {"id": record.get("id"), "referencia": str(reference)}


def _check(
    name: str,
    passed: bool,
    detail: str,
    affected: int = 0,
    affected_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "nombre": name,
        "estado": "Aprobado" if passed else "Requiere atención",
        "detalle": detail,
        "registros_afectados": affected,
        "referencias_afectadas": [
            _record_reference(record) for record in (affected_records or [])
        ],
    }


def _read_collection(filename: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        data = read_json_file(filename, default_data=[])
    except StorageError as error:
        return [], str(error)

    if not isinstance(data, list):
        return [], f"El archivo {filename} debe contener una lista de registros."

    invalid_records = sum(not isinstance(record, dict) for record in data)
    if invalid_records:
        return [], f"El archivo {filename} contiene {invalid_records} registro(s) con formato inválido."

    return data, None


def _validate_suppliers(suppliers: list[dict[str, Any]], read_error: str | None) -> list[dict[str, Any]]:
    if read_error:
        return [_check("Catálogo de proveedores legible", False, read_error, 1)]

    invalid = [
        supplier
        for supplier in suppliers
        if not _is_positive_integer(supplier.get("id"))
        or not _has_text(supplier.get("nombre"))
        or not _has_text(supplier.get("asesor"))
        or not _is_valid_phone(supplier.get("telefono"))
        or not _is_non_negative_integer(supplier.get("dias_credito"))
    ]
    ids = [_key(supplier.get("id")) for supplier in suppliers]
    names = [str(supplier.get("nombre", "")).strip().casefold() for supplier in suppliers]
    invalid_states = [
        supplier
        for supplier in suppliers
        if (supplier.get("estado") or "Pendiente") not in {"Activo", "Inactivo", "Pendiente"}
    ]
    duplicate_ids = len(ids) - len(set(ids))
    duplicate_names = len(names) - len(set(names))

    return [
        _check(
            "Datos obligatorios de proveedores",
            not invalid,
            "Todos los proveedores tienen nombre, asesor, teléfono y días de crédito."
            if not invalid
            else "Hay proveedores con campos obligatorios faltantes o inválidos.",
            len(invalid),
            invalid,
        ),
        _check(
            "Estados de proveedores válidos",
            not invalid_states,
            "Los estados son válidos." if not invalid_states else "Hay estados de proveedor no reconocidos.",
            len(invalid_states),
            invalid_states,
        ),
        _check(
            "Identificadores de proveedores únicos",
            duplicate_ids == 0,
            "No hay identificadores repetidos." if duplicate_ids == 0 else "Hay identificadores repetidos.",
            duplicate_ids,
        ),
        _check(
            "Nombres de proveedores únicos",
            duplicate_names == 0,
            "No hay nombres repetidos." if duplicate_names == 0 else "Hay nombres repetidos.",
            duplicate_names,
        ),
    ]


def _validate_purchases(
    purchases: list[dict[str, Any]],
    suppliers: list[dict[str, Any]],
    read_error: str | None,
    reference_date: date,
) -> list[dict[str, Any]]:
    if read_error:
        return [_check("Registro de compras legible", False, read_error, 1)]

    supplier_ids = {_key(supplier.get("id")) for supplier in suppliers}
    invalid = []
    invalid_dates = []
    future_dates = []
    orphaned = []
    for purchase in purchases:
        required_fields_valid = all(
            _has_text(purchase.get(field))
            for field in ("factura", "sku", "descripcion", "fecha_compra")
        )
        numeric_fields_valid = (
            _is_positive_integer(purchase.get("id"))
            and _is_positive_integer(purchase.get("proveedor_id"))
            and _is_positive_integer(purchase.get("dias_credito"))
            and _is_positive_number(purchase.get("monto_total"))
        )
        if not required_fields_valid or not numeric_fields_valid:
            invalid.append(purchase)

        try:
            purchase_date = parse_date(str(purchase.get("fecha_compra", "")))
        except (TypeError, ValueError):
            invalid_dates.append(purchase)
        else:
            if purchase_date > reference_date:
                future_dates.append(purchase)

        if _key(purchase.get("proveedor_id")) not in supplier_ids:
            orphaned.append(purchase)

    invoices = [str(purchase.get("factura", "")).strip().casefold() for purchase in purchases]
    duplicate_invoices = len(invoices) - len(set(invoices))
    invalid_order_totals = []
    invalid_order_states = []
    for purchase in purchases:
        items = purchase.get("items")
        state = purchase.get("estado")
        if state is not None and state not in PURCHASE_STATES:
            invalid_order_states.append(purchase)
        if not isinstance(items, list) or not items:
            continue

        try:
            subtotal = 0.0
            for item in items:
                quantity = float(item.get("cantidad"))
                unit_price = float(item.get("precio_unitario"))
                if quantity <= 0 or not _has_text(item.get("sku")) or not _has_text(item.get("descripcion")):
                    raise ValueError
                subtotal += quantity * unit_price
            taxes = float(purchase.get("impuestos", 0) or 0)
            total = float(purchase.get("total", purchase.get("monto_total")))
            if taxes < 0 or not isclose(round(subtotal, 2) + round(taxes, 2), round(total, 2), abs_tol=0.01):
                raise ValueError
        except (TypeError, ValueError):
            invalid_order_totals.append(purchase)

    return [
        _check(
            "Datos obligatorios de compras",
            not invalid,
            "Todas las compras tienen información completa y valores positivos."
            if not invalid
            else "Hay compras con campos faltantes o valores inválidos.",
            len(invalid),
            invalid,
        ),
        _check(
            "Fechas de compra válidas",
            not invalid_dates,
            "Todas las fechas usan el formato correcto." if not invalid_dates else "Hay compras con fechas inválidas.",
            len(invalid_dates),
        ),
        _check(
            "Fechas de compra no futuras",
            not future_dates,
            "No hay compras fechadas en el futuro." if not future_dates else "Hay compras con fecha posterior a hoy.",
            len(future_dates),
        ),
        _check(
            "Proveedores relacionados",
            not orphaned,
            "Cada compra apunta a un proveedor registrado." if not orphaned else "Hay compras sin proveedor válido.",
            len(orphaned),
        ),
        _check(
            "Facturas únicas",
            duplicate_invoices == 0,
            "No hay facturas repetidas." if duplicate_invoices == 0 else "Hay facturas repetidas.",
            duplicate_invoices,
        ),
        _check(
            "Totales de órdenes consistentes",
            not invalid_order_totals,
            "Las partidas y totales son consistentes."
            if not invalid_order_totals
            else "Hay órdenes con partidas, impuestos o totales inconsistentes.",
            len(invalid_order_totals),
        ),
        _check(
            "Estados de órdenes válidos",
            not invalid_order_states,
            "Los estados de orden son válidos."
            if not invalid_order_states
            else "Hay órdenes con estados no reconocidos.",
            len(invalid_order_states),
        ),
    ]


def _validate_inventory(
    items: list[dict[str, Any]],
    read_error: str | None,
    movements: list[dict[str, Any]],
    movements_error: str | None,
    reference_date: date,
) -> list[dict[str, Any]]:
    if read_error:
        return [_check("Inventario legible", False, read_error, 1)]

    invalid = []
    for item in items:
        has_required_fields = all(_has_text(item.get(field)) for field in ("sku", "descripcion")) and all(
            field in item for field in INVENTORY_REQUIRED_FIELDS[2:]
        )
        valid_values = (
            _is_non_negative_integer(item.get("stock_actual"))
            and _is_non_negative_integer(item.get("stock_minimo"))
            and _is_positive_number(item.get("valor_unitario"))
            and _is_non_negative_integer(item.get("dias_sin_movimiento"))
        )
        if not has_required_fields or not valid_values:
            invalid.append(item)

    skus = [str(item.get("sku", "")).strip().casefold() for item in items]
    duplicate_skus = len(skus) - len(set(skus))

    inventory_by_sku = {
        str(item.get("sku", "")).strip().casefold(): item
        for item in items
        if _has_text(item.get("sku"))
    }
    invalid_movements = []
    unknown_skus = []
    invalid_movement_dates = []
    future_movement_dates = []
    for movement in movements:
        if (
            movement.get("tipo") not in MOVEMENT_TYPES
            or not _is_positive_integer(movement.get("cantidad"))
            or not _has_text(movement.get("sku"))
            or not _is_positive_integer(movement.get("id"))
            or (
                movement.get("tipo") == "Ajuste"
                and movement.get("direccion") not in {"Incremento", "Decremento"}
            )
        ):
            invalid_movements.append(movement)
        sku = str(movement.get("sku", "")).strip().casefold()
        if sku not in inventory_by_sku:
            unknown_skus.append(movement)
        try:
            movement_date = parse_date(str(movement.get("fecha", "")))
        except (TypeError, ValueError):
            invalid_movement_dates.append(movement)
        else:
            if movement_date > reference_date:
                future_movement_dates.append(movement)

    movement_ids = [_key(movement.get("id")) for movement in movements]
    duplicate_movement_ids = len(movement_ids) - len(set(movement_ids))
    inconsistent_stock = []
    for item in items:
        if "stock_inicial" not in item:
            continue
        try:
            if not _is_non_negative_integer(item.get("stock_inicial")):
                raise ValueError
            initial_stock = float(item.get("stock_inicial"))
            expected_stock = initial_stock
            sku = str(item.get("sku", "")).strip().casefold()
            for movement in movements:
                if str(movement.get("sku", "")).strip().casefold() != sku:
                    continue
                quantity = float(movement.get("cantidad"))
                increases_stock = movement.get("tipo") == "Entrada" or (
                    movement.get("tipo") == "Ajuste"
                    and movement.get("direccion") == "Incremento"
                )
                expected_stock += quantity if increases_stock else -quantity
            if expected_stock != float(item.get("stock_actual")):
                inconsistent_stock.append(item)
        except (TypeError, ValueError):
            inconsistent_stock.append(item)

    movement_checks = []
    if movements_error:
        movement_checks.append(_check("Movimientos de inventario legibles", False, movements_error, 1))
    else:
        movement_checks.extend([
            _check(
                "Datos de movimientos de inventario",
                not invalid_movements,
                "Todos los movimientos tienen tipo, SKU, cantidad e identificador válidos."
                if not invalid_movements
                else "Hay movimientos con campos faltantes o valores inválidos.",
                len(invalid_movements),
                invalid_movements,
            ),
            _check(
                "Movimientos relacionados con SKU",
                not unknown_skus,
                "Todos los movimientos corresponden a un SKU registrado."
                if not unknown_skus
                else "Hay movimientos asociados a SKU inexistentes.",
                len(unknown_skus),
            ),
            _check(
                "Fechas de movimientos válidas",
                not invalid_movement_dates and not future_movement_dates,
                "Las fechas de movimiento son válidas y no futuras."
                if not invalid_movement_dates and not future_movement_dates
                else "Hay movimientos con fechas inválidas o futuras.",
                len(invalid_movement_dates) + len(future_movement_dates),
            ),
            _check(
                "Identificadores de movimientos únicos",
                duplicate_movement_ids == 0,
                "No hay identificadores de movimiento repetidos."
                if duplicate_movement_ids == 0
                else "Hay identificadores de movimiento repetidos.",
                duplicate_movement_ids,
            ),
            _check(
                "Existencias consistentes con movimientos",
                not inconsistent_stock,
                "Las existencias coinciden con el movimiento acumulado cuando existe una línea base."
                if not inconsistent_stock
                else "Hay existencias que no coinciden con sus movimientos acumulados.",
                len(inconsistent_stock),
            ),
        ])

    return [
        _check(
            "Datos obligatorios de inventario",
            not invalid,
            "Todos los artículos tienen descripción y valores válidos."
            if not invalid
            else "Hay artículos con campos faltantes o valores inválidos.",
            len(invalid),
            invalid,
        ),
        _check(
            "SKU únicos",
            duplicate_skus == 0,
            "No hay SKU repetidos." if duplicate_skus == 0 else "Hay SKU repetidos.",
            duplicate_skus,
        ),
    ] + movement_checks


def _validate_process_records(
    processes: list[dict[str, Any]],
    processes_error: str | None,
    quotes: list[dict[str, Any]],
    quotes_error: str | None,
    negotiations: list[dict[str, Any]],
    negotiations_error: str | None,
    events: list[dict[str, Any]],
    events_error: str | None,
    incidents: list[dict[str, Any]],
    incidents_error: str | None,
    receipts: list[dict[str, Any]],
    receipts_error: str | None,
    payments: list[dict[str, Any]],
    payments_error: str | None,
    payment_movements: list[dict[str, Any]],
    payment_movements_error: str | None,
    suppliers: list[dict[str, Any]],
    purchases: list[dict[str, Any]],
    reference_date: date,
) -> list[dict[str, Any]]:
    """Revisa la integridad del expediente integrado sin modificar datos."""

    if processes_error:
        return [_check("Expedientes de compra legibles", False, processes_error, 1)]

    process_ids = {_key(item.get("id")) for item in processes}
    supplier_ids = {_key(item.get("id")) for item in suppliers}
    orders_by_id = {_key(item.get("id")): item for item in purchases}
    quotes_by_id = {_key(item.get("id")): item for item in quotes}
    payment_by_id = {_key(item.get("id")): item for item in payments}

    invalid_processes = []
    future_processes = []
    orphaned_process_suppliers = []
    for process in processes:
        valid = (
            _is_positive_integer(process.get("id"))
            and bool(re.fullmatch(r"PC-\d{4}-\d{4}", str(process.get("folio", ""))))
            and _has_text(process.get("necesidad"))
            and process.get("estado") in PROCESS_STATES
            and process.get("prioridad") in PROCESS_PRIORITIES
        )
        try:
            process_date = parse_date(str(process.get("fecha_creacion", "")))
        except (TypeError, ValueError):
            valid = False
        else:
            if process_date > reference_date:
                future_processes.append(process)
        if process.get("proveedor_id") not in (None, "") and _key(process.get("proveedor_id")) not in supplier_ids:
            orphaned_process_suppliers.append(process)
        if not valid:
            invalid_processes.append(process)

    process_ids_count = len(processes) - len(process_ids)
    duplicate_folios = len(processes) - len({str(item.get("folio", "")).strip().casefold() for item in processes})
    invalid_selected_quotes = [
        process
        for process in processes
        if process.get("cotizacion_seleccionada_id") not in (None, "")
        and not (
            _key(process.get("cotizacion_seleccionada_id")) in quotes_by_id
            and quotes_by_id[_key(process.get("cotizacion_seleccionada_id"))].get("proceso_id") == process.get("id")
        )
    ]

    invalid_quotes = []
    selected_per_process: dict[Any, int] = {}
    for quote in quotes:
        try:
            quantity = float(quote.get("cantidad"))
            unit_price = float(quote.get("precio_unitario"))
            subtotal = float(quote.get("subtotal"))
            shipping = float(quote.get("envio", 0) or 0)
            taxes = float(quote.get("impuestos", 0) or 0)
            total = float(quote.get("costo_total"))
            totals_valid = (
                quantity > 0
                and unit_price > 0
                and shipping >= 0
                and taxes >= 0
                and isclose(subtotal, quantity * unit_price, abs_tol=0.01)
                and isclose(total, subtotal + shipping + taxes, abs_tol=0.01)
            )
        except (TypeError, ValueError):
            totals_valid = False
        if (
            not _is_positive_integer(quote.get("id"))
            or _key(quote.get("proceso_id")) not in process_ids
            or _key(quote.get("proveedor_id")) not in supplier_ids
            or not _has_text(quote.get("sku"))
            or not _has_text(quote.get("descripcion"))
            or not totals_valid
        ):
            invalid_quotes.append(quote)
        if quote.get("seleccionada"):
            process_key = _key(quote.get("proceso_id"))
            selected_per_process[process_key] = selected_per_process.get(process_key, 0) + 1

    duplicate_quote_ids = len(quotes) - len({_key(item.get("id")) for item in quotes})
    multiple_selected_quotes = [
        {"id": process_id}
        for process_id, count in selected_per_process.items()
        if count > 1
    ]

    invalid_negotiations = []
    for negotiation in negotiations:
        quote = quotes_by_id.get(_key(negotiation.get("cotizacion_id")))
        original = negotiated = savings = quantity = 0.0
        try:
            original = float(negotiation.get("precio_cotizado"))
            negotiated = float(negotiation.get("precio_negociado"))
            savings = float(negotiation.get("ahorro_total"))
            quantity = float(quote.get("cantidad")) if quote else 0
            savings_valid = isclose(savings, round((original - negotiated) * quantity, 2), abs_tol=0.01)
        except (TypeError, ValueError):
            savings_valid = False
        if (
            not _is_positive_integer(negotiation.get("id"))
            or _key(negotiation.get("proceso_id")) not in process_ids
            or quote is None
            or quote.get("proceso_id") != negotiation.get("proceso_id")
            or original <= 0
            or negotiated <= 0
            or not savings_valid
        ):
            invalid_negotiations.append(negotiation)

    invalid_relations = []
    for record in events + incidents + receipts:
        if _key(record.get("proceso_id")) not in process_ids:
            invalid_relations.append(record)
            continue
        if record.get("orden_id") not in (None, ""):
            order = orders_by_id.get(_key(record.get("orden_id")))
            if order is None or order.get("proceso_id") != record.get("proceso_id"):
                invalid_relations.append(record)
    invalid_incidents = [
        incident
        for incident in incidents
        if incident.get("estado") not in INCIDENT_STATES
        or not _has_text(incident.get("descripcion"))
        or not _has_text(incident.get("tipo"))
    ]
    invalid_receipts = [
        receipt
        for receipt in receipts
        if not isinstance(receipt.get("items"), list)
        or not receipt.get("items")
        or any(
            not _has_text(item.get("sku"))
            or not _is_non_negative_integer(item.get("cantidad_recibida"))
            or not _is_non_negative_integer(item.get("cantidad_aceptada"))
            or not _is_non_negative_integer(item.get("cantidad_rechazada"))
            or int(item.get("cantidad_aceptada", 0)) + int(item.get("cantidad_rechazada", 0)) != int(item.get("cantidad_recibida", 0))
            for item in receipt.get("items", [])
        )
    ]

    invalid_payments = []
    for payment in payments:
        try:
            amount = float(payment.get("monto"))
            paid = float(payment.get("monto_pagado", 0) or 0)
            balance = float(payment.get("saldo"))
            balance_valid = isclose(balance, amount - paid, abs_tol=0.01)
        except (TypeError, ValueError):
            amount = paid = 0
            balance_valid = False
        if (
            not _is_positive_integer(payment.get("id"))
            or _key(payment.get("proceso_id")) not in process_ids
            or _key(payment.get("orden_id")) not in orders_by_id
            or amount <= 0
            or paid < 0
            or paid > amount
            or not balance_valid
            or payment.get("estado") not in {"pendiente", "parcial", "pagado", "vencido"}
        ):
            invalid_payments.append(payment)

    invalid_payment_movements = []
    movement_totals: dict[Any, float] = {}
    for movement in payment_movements:
        payment_key = _key(movement.get("pago_id"))
        try:
            amount = float(movement.get("monto"))
        except (TypeError, ValueError):
            amount = 0
        movement_totals[payment_key] = movement_totals.get(payment_key, 0) + amount
        if payment_key not in payment_by_id or not _is_positive_number(movement.get("monto")):
            invalid_payment_movements.append(movement)
    for payment_key, total_paid in movement_totals.items():
        payment = payment_by_id.get(payment_key)
        if payment and total_paid > float(payment.get("monto", 0) or 0) + 0.01:
            invalid_payment_movements.append(payment)

    unreadable_checks = [
        ("Cotizaciones legibles", quotes_error, QUOTES_FILE),
        ("Negociaciones legibles", negotiations_error, NEGOTIATIONS_FILE),
        ("Seguimiento legible", events_error, EVENTS_FILE),
        ("Incidencias legibles", incidents_error, INCIDENTS_FILE),
        ("Recepciones legibles", receipts_error, RECEIPTS_FILE),
        ("Pagos legibles", payments_error, PAYMENTS_FILE),
        ("Movimientos de pago legibles", payment_movements_error, PAYMENT_MOVEMENTS_FILE),
    ]
    checks = [
        _check("Datos básicos de expedientes", not invalid_processes, "Los expedientes tienen folio, necesidad, prioridad y estado válidos." if not invalid_processes else "Hay expedientes con datos básicos inválidos.", len(invalid_processes), invalid_processes),
        _check("Fechas de expedientes no futuras", not future_processes, "Las fechas de creación no son futuras." if not future_processes else "Hay expedientes con fecha futura.", len(future_processes), future_processes),
        _check("Relaciones de expedientes", not orphaned_process_suppliers and not invalid_selected_quotes and not invalid_relations, "Las relaciones de proveedor, cotización, orden y seguimiento son válidas." if not orphaned_process_suppliers and not invalid_selected_quotes and not invalid_relations else "Hay relaciones que apuntan a registros inexistentes o incompatibles.", len(orphaned_process_suppliers) + len(invalid_selected_quotes) + len(invalid_relations), orphaned_process_suppliers + invalid_selected_quotes + invalid_relations),
        _check("Cotizaciones consistentes", not invalid_quotes and duplicate_quote_ids == 0 and not multiple_selected_quotes, "Las cotizaciones tienen totales e identificadores consistentes." if not invalid_quotes and duplicate_quote_ids == 0 and not multiple_selected_quotes else "Hay cotizaciones con totales, identificadores o selección inconsistente.", len(invalid_quotes) + duplicate_quote_ids + len(multiple_selected_quotes), invalid_quotes),
        _check("Negociaciones trazables", not invalid_negotiations, "Las negociaciones conservan cotización, proceso y ahorro calculable." if not invalid_negotiations else "Hay negociaciones con relaciones o ahorros inconsistentes.", len(invalid_negotiations), invalid_negotiations),
        _check("Recepciones e incidencias válidas", not invalid_receipts and not invalid_incidents, "Las recepciones e incidencias tienen estructura y estados válidos." if not invalid_receipts and not invalid_incidents else "Hay recepciones o incidencias con datos inválidos.", len(invalid_receipts) + len(invalid_incidents), invalid_receipts + invalid_incidents),
        _check("Saldos de pagos consistentes", not invalid_payments and not invalid_payment_movements, "Los saldos y aplicaciones de pago son consistentes." if not invalid_payments and not invalid_payment_movements else "Hay obligaciones o aplicaciones de pago que requieren atención.", len(invalid_payments) + len(invalid_payment_movements), invalid_payments + invalid_payment_movements),
    ]
    checks.extend(
        _check(f"{label}", not error, f"{filename} se puede consultar." if not error else error, 0 if not error else 1)
        for label, error, filename in unreadable_checks
    )
    checks.extend([
        _check("Identificadores de expedientes únicos", process_ids_count == 0 and duplicate_folios == 0, "No hay folios o identificadores repetidos." if process_ids_count == 0 and duplicate_folios == 0 else "Hay identificadores o folios repetidos.", process_ids_count + duplicate_folios),
    ])
    return checks


def run_quality_assurance(reference_date: date | None = None) -> dict[str, Any]:
    """Ejecuta las validaciones operativas y devuelve un informe legible."""

    today = reference_date or date.today()
    suppliers, suppliers_error = _read_collection(SUPPLIERS_FILE)
    purchases, purchases_error = _read_collection(PURCHASES_FILE)
    inventory, inventory_error = _read_collection(INVENTORY_FILE)
    movements, movements_error = _read_collection(MOVEMENTS_FILE)
    processes, processes_error = _read_collection(PROCESSES_FILE)
    quotes, quotes_error = _read_collection(QUOTES_FILE)
    negotiations, negotiations_error = _read_collection(NEGOTIATIONS_FILE)
    events, events_error = _read_collection(EVENTS_FILE)
    incidents, incidents_error = _read_collection(INCIDENTS_FILE)
    receipts, receipts_error = _read_collection(RECEIPTS_FILE)
    payments, payments_error = _read_collection(PAYMENTS_FILE)
    payment_movements, payment_movements_error = _read_collection(PAYMENT_MOVEMENTS_FILE)

    checks: list[dict[str, Any]] = []
    checks.extend(_validate_suppliers(suppliers, suppliers_error))
    checks.extend(_validate_purchases(purchases, suppliers, purchases_error, today))
    checks.extend(
        _validate_inventory(inventory, inventory_error, movements, movements_error, today)
    )
    checks.extend(
        _validate_process_records(
            processes,
            processes_error,
            quotes,
            quotes_error,
            negotiations,
            negotiations_error,
            events,
            events_error,
            incidents,
            incidents_error,
            receipts,
            receipts_error,
            payments,
            payments_error,
            payment_movements,
            payment_movements_error,
            suppliers,
            purchases,
            today,
        )
    )

    failed = sum(check["estado"] != "Aprobado" for check in checks)
    return {
        "fecha_revision": today.isoformat(),
        "estado": "Aprobado" if failed == 0 else "Requiere atención",
        "resumen": {
            "validaciones": len(checks),
            "aprobadas": len(checks) - failed,
            "observaciones": failed,
        },
        "validaciones": checks,
    }
