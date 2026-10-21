"""Medición reproducible del impacto operativo de la herramienta."""

from __future__ import annotations

from datetime import date, datetime
from statistics import mean, median, stdev
from typing import Any

from .storage import next_record_id, read_json_file, write_json_file


EVALUATIONS_FILE = "evaluaciones.json"
EVALUATION_METHODS = {"manual", "sistema"}
EVALUATION_TASKS = {
    "registro_proveedor",
    "buscar_proveedor",
    "comparar_cotizaciones",
    "generar_orden",
    "consultar_estado",
    "generar_reporte",
}


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"El campo '{field_name}' es obligatorio.")
    return result


def _non_negative_number(value: Any, field_name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser numérico.") from error
    if result < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")
    return round(result, 2)


def _non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"El campo '{field_name}' debe ser entero no negativo.")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{field_name}' debe ser entero no negativo.") from error
    if result < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")
    return result


def _date_text(value: Any) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError("La fecha es obligatoria.")
    try:
        observed_date = datetime.strptime(result, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from error
    if observed_date > date.today():
        raise ValueError("La fecha no puede ser futura.")
    return result


def load_evaluations() -> list[dict[str, Any]]:
    data = read_json_file(EVALUATIONS_FILE, default_data=[])
    return data if isinstance(data, list) else []


def create_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    task = _text(payload.get("tarea"), "tarea").casefold()
    method = _text(payload.get("metodo"), "método").casefold()
    if task not in EVALUATION_TASKS:
        raise ValueError("La tarea de evaluación no es válida.")
    if method not in EVALUATION_METHODS:
        raise ValueError("El método debe ser manual o sistema.")
    evaluations = load_evaluations()
    evaluation = {
        "id": next_record_id(evaluations),
        "fecha": _date_text(payload.get("fecha", date.today().isoformat())),
        "tarea": task,
        "metodo": method,
        "duracion_segundos": _non_negative_number(payload.get("duracion_segundos"), "duración"),
        "errores_detectados": _non_negative_integer(payload.get("errores_detectados", 0), "errores_detectados"),
        "responsable": str(payload.get("responsable") or "").strip(),
        "observaciones": str(payload.get("observaciones") or "").strip(),
        "created_at": _now(),
    }
    evaluations.append(evaluation)
    write_json_file(EVALUATIONS_FILE, evaluations)
    return evaluation


def list_evaluations(task: str = "", method: str = "") -> list[dict[str, Any]]:
    task = str(task or "").strip().casefold()
    method = str(method or "").strip().casefold()
    records = [
        item for item in load_evaluations()
        if (not task or item.get("tarea") == task)
        and (not method or item.get("metodo") == method)
    ]
    return sorted(records, key=lambda item: (item.get("fecha", ""), item.get("id", 0)), reverse=True)


def _stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [float(item["duracion_segundos"]) for item in records]
    errors = sum(int(item.get("errores_detectados", 0) or 0) for item in records)
    return {
        "n": len(records),
        "media_segundos": round(mean(durations), 2) if durations else None,
        "mediana_segundos": round(median(durations), 2) if durations else None,
        "minimo_segundos": round(min(durations), 2) if durations else None,
        "maximo_segundos": round(max(durations), 2) if durations else None,
        "desviacion_estandar_segundos": round(stdev(durations), 2) if len(durations) >= 2 else None,
        "errores": errors,
        "tasa_error_pct": round((errors / len(records)) * 100, 2) if records else None,
    }


def build_evaluation_summary(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    records = records if records is not None else load_evaluations()
    groups = []
    for task in sorted(EVALUATION_TASKS):
        for method in ("manual", "sistema"):
            group_records = [item for item in records if item.get("tarea") == task and item.get("metodo") == method]
            groups.append({"tarea": task, "metodo": method, **_stats(group_records)})

    comparisons = []
    for task in sorted(EVALUATION_TASKS):
        manual = next(item for item in groups if item["tarea"] == task and item["metodo"] == "manual")
        system = next(item for item in groups if item["tarea"] == task and item["metodo"] == "sistema")
        manual_mean = manual["media_segundos"]
        system_mean = system["media_segundos"]
        comparisons.append({
            "tarea": task,
            "manual_n": manual["n"],
            "manual_mean_segundos": manual_mean,
            "system_n": system["n"],
            "system_mean_segundos": system_mean,
            "reduccion_tiempo_pct": round((manual_mean - system_mean) / manual_mean * 100, 2)
            if manual_mean not in (None, 0) and system_mean is not None
            else None,
            "manual_error_rate_pct": manual["tasa_error_pct"],
            "system_error_rate_pct": system["tasa_error_pct"],
        })
    return {"registros": len(records), "grupos": groups, "comparaciones": comparisons}


def build_operational_metrics(reference_date: date | None = None) -> list[dict[str, Any]]:
    """Prepara filas exportables a partir de indicadores existentes."""

    from .analisis import build_dashboard
    from .inventario import build_inventory_dashboard
    from .qa import run_quality_assurance

    today = reference_date or date.today()
    dashboard = build_dashboard(today)
    inventory = build_inventory_dashboard(today)
    qa = run_quality_assurance(today)
    summary = dashboard["resumen"]
    inventory_summary = inventory["resumen"]
    qa_summary = qa["resumen"]
    values = [
        ("proveedores_total", summary.get("proveedores"), summary.get("proveedores")),
        ("compras_total", summary.get("compras"), summary.get("compras")),
        ("monto_total_compras", summary.get("monto_total"), summary.get("compras")),
        ("monto_vencido", summary.get("monto_vencido"), summary.get("compras_vencidas")),
        ("procesos_abiertos", summary.get("procesos_abiertos"), summary.get("procesos")),
        ("incidencias_abiertas", summary.get("incidencias_abiertas"), summary.get("incidencias_abiertas")),
        ("pagos_vencidos", summary.get("pagos_vencidos"), summary.get("pagos_vencidos")),
        ("inventario_bajo", inventory_summary.get("inventario_bajo"), inventory_summary.get("items_monitoreados")),
        ("inventario_rezagado", inventory_summary.get("inventario_rezagado"), inventory_summary.get("items_monitoreados")),
        ("qa_validaciones_aprobadas", qa_summary.get("aprobadas"), qa_summary.get("validaciones")),
    ]
    return [
        {"kpi": name, "valor": value, "periodo": today.isoformat(), "fecha_calculo": today.isoformat(), "n": n}
        for name, value, n in values
    ]
