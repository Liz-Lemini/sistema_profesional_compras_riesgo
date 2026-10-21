"""Indicadores operativos de compras y vencimientos por proveedor."""

from __future__ import annotations

from datetime import date, datetime
from statistics import mean
from typing import Any

from .storage import read_json_file


SUPPLIERS_FILE = "proveedores.json"
PURCHASES_FILE = "compras.json"


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def calculate_remaining_days(
    purchase_date: str,
    credit_days: int,
    reference_date: date | None = None,
) -> int:
    """Calcula los días restantes del crédito desde una fecha de corte."""

    today = reference_date or date.today()
    elapsed_days = (today - parse_date(purchase_date)).days
    return int(credit_days) - elapsed_days


def classify_attention(overdue_count: int) -> str:
    """Regla operativa explícita: cualquier vencimiento requiere atención."""

    return "Requiere atención" if overdue_count else "Sin vencimientos"


def load_suppliers() -> list[dict[str, Any]]:
    data = read_json_file(SUPPLIERS_FILE, default_data=[])
    return data if isinstance(data, list) else []


def load_purchases() -> list[dict[str, Any]]:
    data = read_json_file(PURCHASES_FILE, default_data=[])
    return data if isinstance(data, list) else []


def _purchase_amount(purchase: dict[str, Any]) -> float:
    return float(purchase.get("monto_total", 0) or 0)


def calculate_supplier_risk(
    supplier: dict[str, Any],
    purchases: list[dict[str, Any]],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Construye indicadores de exposición; no calcula un score predictivo."""

    today = reference_date or date.today()
    supplier_contact = supplier.get("correo") or supplier.get("contacto", "Sin contacto")
    supplier_purchases = [
        purchase
        for purchase in purchases
        if purchase.get("proveedor_id") == supplier.get("id")
    ]

    remaining_days = [
        calculate_remaining_days(
            purchase["fecha_compra"],
            int(purchase["dias_credito"]),
            reference_date=today,
        )
        for purchase in supplier_purchases
    ]
    overdue_pairs = [
        (purchase, days)
        for purchase, days in zip(supplier_purchases, remaining_days)
        if days < 0
    ]
    overdue_days = [abs(days) for _, days in overdue_pairs]
    overdue_count = len(overdue_pairs)
    total_amount = sum(_purchase_amount(purchase) for purchase in supplier_purchases)
    overdue_amount = sum(_purchase_amount(purchase) for purchase, _ in overdue_pairs)
    average_delay = mean(overdue_days) if overdue_days else 0.0
    average_credit_days = (
        mean(int(purchase.get("dias_credito", 0)) for purchase in supplier_purchases)
        if supplier_purchases
        else 0.0
    )
    total_count = len(supplier_purchases)

    detailed_purchases = []
    for purchase, days in zip(supplier_purchases, remaining_days):
        detailed_purchases.append(
            {
                "factura": purchase.get("factura"),
                "sku": purchase.get("sku"),
                "descripcion": purchase.get("descripcion"),
                "fecha_compra": purchase.get("fecha_compra"),
                "dias_credito": int(purchase.get("dias_credito", 0)),
                "monto_total": _purchase_amount(purchase),
                "dias_restantes": days,
                "remaining_days": days,
                "estado_credito": "Vencida" if days < 0 else "Vigente",
            }
        )

    return {
        "proveedor_id": supplier.get("id"),
        "proveedor": supplier.get("nombre", "Sin nombre"),
        "sector": supplier.get("sector", "Sin sector"),
        "contacto": supplier_contact or "Sin contacto",
        "nivel_atencion": classify_attention(overdue_count),
        "metricas": {
            "atraso_promedio_dias": round(average_delay, 2),
            "dias_maximo_atraso": max(overdue_days, default=0),
            "frecuencia_vencida_pct": round((overdue_count / total_count) * 100, 2)
            if total_count
            else 0.0,
            "dias_credito_promedio": round(average_credit_days, 2),
            "monto_total_compras": round(total_amount, 2),
            "monto_vencido": round(overdue_amount, 2),
            "facturas_vencidas": overdue_count,
            "total_facturas": total_count,
        },
        "compras": detailed_purchases,
    }


def build_dashboard(reference_date: date | None = None) -> dict[str, Any]:
    today = reference_date or date.today()
    suppliers = load_suppliers()
    purchases = load_purchases()

    provider_reports = [
        calculate_supplier_risk(supplier, purchases, reference_date=today)
        for supplier in suppliers
    ]
    provider_reports.sort(
        key=lambda item: (
            item["metricas"]["monto_vencido"],
            item["metricas"]["dias_maximo_atraso"],
            item["metricas"]["facturas_vencidas"],
        ),
        reverse=True,
    )

    overdue_purchases = sum(
        report["metricas"]["facturas_vencidas"] for report in provider_reports
    )
    overdue_amount = sum(
        report["metricas"]["monto_vencido"] for report in provider_reports
    )
    total_amount = sum(_purchase_amount(purchase) for purchase in purchases)
    process_indicators = build_process_indicators(today)

    return {
        "fecha_corte": today.isoformat(),
        "resumen": {
            "proveedores": len(suppliers),
            "compras": len(purchases),
            "compras_vencidas": overdue_purchases,
            "monto_total": round(total_amount, 2),
            "monto_vencido": round(overdue_amount, 2),
            **process_indicators["resumen"],
        },
        "proveedores": provider_reports,
        "procesos": process_indicators,
    }


def build_process_indicators(reference_date: date | None = None) -> dict[str, Any]:
    """Resume atención de expedientes con reglas trazables y sin pronósticos."""

    today = reference_date or date.today()
    from .proceso import (
        INCIDENTS_FILE,
        PAYMENTS_FILE,
        PROCESSES_FILE,
        load_incidents,
        load_payments,
        load_processes,
    )
    from .inventario import list_inventory

    # Las funciones de carga conservan la misma capa JSON que el resto del MVP.
    processes = load_processes()
    suppliers = load_suppliers()
    incidents = load_incidents()
    payments = load_payments()
    closed_states = {"completado", "cancelado"}
    open_processes = [item for item in processes if item.get("estado") not in closed_states]
    process_states = {
        state: sum(1 for item in processes if item.get("estado") == state)
        for state in sorted({item.get("estado") for item in processes if item.get("estado")})
    }

    alerts = []
    for process in open_processes:
        if process.get("prioridad") in {"Alta", "Urgente"}:
            alerts.append({
                "tipo": "proceso_prioritario",
                "prioridad": "Alta" if process.get("prioridad") == "Alta" else "Urgente",
                "mensaje": f"{process.get('folio', 'Proceso')} tiene prioridad {process.get('prioridad')}.",
                "proceso_id": process.get("id"),
                "folio": process.get("folio"),
            })

    stale_processes = []
    for process in open_processes:
        try:
            updated = parse_date(str(process.get("updated_at", ""))[:10])
        except (TypeError, ValueError):
            continue
        if (today - updated).days >= 7:
            stale_processes.append(process)
            alerts.append({
                "tipo": "proceso_estancado",
                "prioridad": "Alta",
                "mensaje": f"{process.get('folio', 'Proceso')} no registra actualización en 7 días o más.",
                "proceso_id": process.get("id"),
                "folio": process.get("folio"),
            })

    open_incidents = [
        item for item in incidents
        if item.get("estado") in {"abierta", "en_revision"}
    ]
    for incident in open_incidents:
        alerts.append({
            "tipo": "incidencia_abierta",
            "prioridad": "Alta",
            "mensaje": f"Incidencia {incident.get('folio', incident.get('id'))} requiere seguimiento.",
            "proceso_id": incident.get("proceso_id"),
            "folio": incident.get("folio"),
        })

    incomplete_suppliers = [
        item for item in suppliers
        if not all(str(item.get(field, "")).strip() for field in ("nombre", "asesor", "telefono"))
        or item.get("dias_credito") in (None, "")
    ]
    for supplier in incomplete_suppliers:
        alerts.append({
            "tipo": "proveedor_incompleto",
            "prioridad": "Media",
            "mensaje": f"El proveedor {supplier.get('nombre', supplier.get('id'))} tiene información pendiente.",
            "proveedor_id": supplier.get("id"),
        })

    overdue_payments = []
    upcoming_payments = []
    for payment in payments:
        try:
            due_date = parse_date(str(payment.get("fecha_vencimiento", "")))
            balance = float(payment.get("saldo", payment.get("monto", 0)) or 0)
        except (TypeError, ValueError):
            continue
        if balance > 0 and due_date < today:
            overdue_payments.append(payment)
            alerts.append({
                "tipo": "pago_vencido",
                "prioridad": "Alta",
                "mensaje": f"El pago {payment.get('folio', payment.get('id'))} tiene saldo vencido.",
                "proceso_id": payment.get("proceso_id"),
                "folio": payment.get("folio"),
            })
        elif balance > 0 and 0 <= (due_date - today).days <= 7:
            upcoming_payments.append(payment)
            alerts.append({
                "tipo": "pago_por_vencer",
                "prioridad": "Media",
                "mensaje": f"El pago {payment.get('folio', payment.get('id'))} vence en {(due_date - today).days} día(s).",
                "proceso_id": payment.get("proceso_id"),
                "folio": payment.get("folio"),
            })

    from .proceso import load_receipts

    partial_receipts = [item for item in load_receipts() if item.get("estado") == "recepcion_parcial"]
    for receipt in partial_receipts:
        alerts.append({
            "tipo": "recepcion_parcial",
            "prioridad": "Alta",
            "mensaje": f"La recepción {receipt.get('folio', receipt.get('id'))} está incompleta.",
            "proceso_id": receipt.get("proceso_id"),
            "folio": receipt.get("folio"),
        })

    delayed_orders = []
    for order in load_purchases():
        if order.get("estado") in {"Recibida", "Cancelada"} or not order.get("fecha_entrega"):
            continue
        try:
            delivery_date = parse_date(str(order.get("fecha_entrega")))
        except ValueError:
            continue
        if delivery_date < today:
            delayed_orders.append(order)
            alerts.append({
                "tipo": "orden_retrasada",
                "prioridad": "Alta",
                "mensaje": f"La orden {order.get('numero_orden', order.get('id'))} tiene fecha de entrega vencida.",
                "proceso_id": order.get("proceso_id"),
                "folio": order.get("numero_orden"),
            })

    low_inventory = [item for item in list_inventory() if item.get("existencia_baja")]
    for item in low_inventory:
        alerts.append({
            "tipo": "inventario_bajo",
            "prioridad": "Media",
            "mensaje": f"El inventario de {item.get('sku')} está en el mínimo o por debajo.",
            "folio": item.get("sku"),
        })

    alerts.sort(key=lambda item: (item["prioridad"] != "Urgente", item["prioridad"] != "Alta", str(item.get("folio", ""))))
    return {
        "resumen": {
            "procesos": len(processes),
            "procesos_abiertos": len(open_processes),
            "procesos_por_estado": process_states,
            "incidencias_abiertas": len(open_incidents),
            "pagos_vencidos": len(overdue_payments),
            "pagos_por_vencer": len(upcoming_payments),
            "ordenes_retrasadas": len(delayed_orders),
            "recepciones_parciales": len(partial_receipts),
            "procesos_estancados": len(stale_processes),
            "proveedores_incompletos": len(incomplete_suppliers),
            "inventario_bajo": len(low_inventory),
            "alertas": len(alerts),
        },
        "alertas": alerts[:50],
        "fuentes": {
            "procesos": PROCESSES_FILE,
            "incidencias": INCIDENTS_FILE,
            "pagos": PAYMENTS_FILE,
        },
    }
