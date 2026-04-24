"""Analitica de inventario rezagado y estudio de mercado."""

from __future__ import annotations

from datetime import date
from typing import Any

from .storage import read_json_file


INVENTORY_FILE = "inventario.json"


def load_inventory() -> list[dict[str, Any]]:
    data = read_json_file(INVENTORY_FILE, default_data=[])
    return data if isinstance(data, list) else []


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


def build_inventory_dashboard(reference_date: date | None = None) -> dict[str, Any]:
    today = reference_date or date.today()
    inventory = load_inventory()

    lagged_items: list[dict[str, Any]] = []
    market_studies: list[dict[str, Any]] = []

    for item in inventory:
        stock_actual = int(item.get("stock_actual", 0) or 0)
        stock_minimo = int(item.get("stock_minimo", 0) or 0)
        unit_value = float(item.get("valor_unitario", 0) or 0)
        days_without_movement = int(item.get("dias_sin_movimiento", 0) or 0)
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

        market_price = float(item.get("precio_referencia_mercado", 0) or 0)
        last_cost = float(item.get("ultimo_costo_compra", 0) or 0)
        variation_pct = round(
            ((last_cost - market_price) / market_price) * 100,
            2,
        ) if market_price else 0.0
        potential_saving = round(max(last_cost - market_price, 0) * stock_actual, 2)

        if variation_pct >= 8:
            recommendation = "Renegociar inmediatamente"
            opportunity = "Alta"
            color = "danger"
        elif variation_pct >= 3:
            recommendation = "Revisar cotizaciones del mercado"
            opportunity = "Media"
            color = "warning"
        else:
            recommendation = "Mantener estrategia actual"
            opportunity = "Baja"
            color = "success"

        market_studies.append(
            {
                "sku": item.get("sku"),
                "descripcion": item.get("descripcion"),
                "proveedor_principal": item.get("proveedor_principal"),
                "ultimo_costo_compra": round(last_cost, 2),
                "precio_referencia_mercado": round(market_price, 2),
                "variacion_pct": variation_pct,
                "tendencia_mercado": item.get("tendencia_mercado", "Sin dato"),
                "oportunidad": opportunity,
                "color": color,
                "ahorro_potencial": potential_saving,
                "recomendacion": recommendation,
            }
        )

    lagged_items.sort(
        key=lambda item: (item["valor_inmovilizado"], item["dias_sin_movimiento"]),
        reverse=True,
    )
    market_studies.sort(
        key=lambda item: (item["ahorro_potencial"], item["variacion_pct"]),
        reverse=True,
    )

    total_immobilized_value = round(
        sum(item["valor_inmovilizado"] for item in lagged_items),
        2,
    )
    total_potential_saving = round(
        sum(item["ahorro_potencial"] for item in market_studies),
        2,
    )

    return {
        "fecha_corte": today.isoformat(),
        "resumen": {
            "items_monitoreados": len(inventory),
            "inventario_rezagado": len(lagged_items),
            "capital_inmovilizado": total_immobilized_value,
            "ahorro_potencial": total_potential_saving,
        },
        "inventario_rezagado": lagged_items,
        "estudio_mercado": market_studies,
    }
