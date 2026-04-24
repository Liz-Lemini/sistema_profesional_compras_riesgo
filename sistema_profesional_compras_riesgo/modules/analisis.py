"""Logica actuarial para el dashboard de riesgo crediticio."""

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
    """Aplica RemainingDays = CreditDays - (Today - PurchaseDate)."""

    today = reference_date or date.today()
    elapsed_days = (today - parse_date(purchase_date)).days
    return int(credit_days) - elapsed_days


def classify_risk(score: float) -> str:
    if score <= 30:
        return "Bajo"
    if score <= 70:
        return "Medio"
    return "Alto"


def risk_color(level: str) -> str:
    return {
        "Bajo": "success",
        "Medio": "warning",
        "Alto": "danger",
    }.get(level, "secondary")


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
    today = reference_date or date.today()
    supplier_purchases = [
        purchase for purchase in purchases if purchase.get("proveedor_id") == supplier.get("id")
    ]

    if not supplier_purchases:
        return {
            "proveedor_id": supplier.get("id"),
            "proveedor": supplier.get("nombre", "Sin nombre"),
            "sector": supplier.get("sector", "Sin sector"),
            "contacto": supplier.get("contacto", "Sin contacto"),
            "score": 0.0,
            "clasificacion": "Bajo",
            "color": "success",
            "metricas": {
                "atraso_promedio_dias": 0.0,
                "componente_atraso": 0.0,
                "uso_credito_pct": 0.0,
                "frecuencia_vencida_pct": 0.0,
                "limite_estimado": 0.0,
                "monto_total_compras": 0.0,
                "facturas_vencidas": 0,
                "total_facturas": 0,
            },
        }

    remaining_days = [
        calculate_remaining_days(
            purchase["fecha_compra"],
            int(purchase["dias_credito"]),
            reference_date=today,
        )
        for purchase in supplier_purchases
    ]
    overdue_days = [abs(days) for days in remaining_days if days < 0]
    overdue_count = len(overdue_days)

    total_amount = sum(_purchase_amount(purchase) for purchase in supplier_purchases)
    average_purchase = total_amount / len(supplier_purchases)
    estimated_limit = average_purchase * 2.5

    average_delay = mean(overdue_days) if overdue_days else 0.0
    delay_component = min((average_delay / 60) * 100, 100)
    usage_component = (
        min((total_amount / estimated_limit) * 100, 100) if estimated_limit else 0.0
    )
    overdue_frequency = (overdue_count / len(supplier_purchases)) * 100

    score = round(
        (delay_component * 0.40)
        + (usage_component * 0.30)
        + (overdue_frequency * 0.30),
        2,
    )
    level = classify_risk(score)

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
                "remaining_days": days,
                "estado_credito": "Vencida" if days < 0 else "Vigente",
            }
        )

    return {
        "proveedor_id": supplier.get("id"),
        "proveedor": supplier.get("nombre", "Sin nombre"),
        "sector": supplier.get("sector", "Sin sector"),
        "contacto": supplier.get("contacto", "Sin contacto"),
        "score": score,
        "clasificacion": level,
        "color": risk_color(level),
        "metricas": {
            "atraso_promedio_dias": round(average_delay, 2),
            "componente_atraso": round(delay_component, 2),
            "uso_credito_pct": round(usage_component, 2),
            "frecuencia_vencida_pct": round(overdue_frequency, 2),
            "limite_estimado": round(estimated_limit, 2),
            "monto_total_compras": round(total_amount, 2),
            "facturas_vencidas": overdue_count,
            "total_facturas": len(supplier_purchases),
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
    provider_reports.sort(key=lambda item: item["score"], reverse=True)

    total_purchases = len(purchases)
    total_amount = sum(_purchase_amount(purchase) for purchase in purchases)
    average_score = round(
        sum(report["score"] for report in provider_reports) / len(provider_reports), 2
    ) if provider_reports else 0.0

    return {
        "fecha_corte": today.isoformat(),
        "resumen": {
            "proveedores": len(suppliers),
            "compras": total_purchases,
            "monto_total": round(total_amount, 2),
            "score_promedio": average_score,
        },
        "proveedores": provider_reports,
    }
