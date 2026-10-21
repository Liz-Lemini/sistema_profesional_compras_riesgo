"""Servidor Flask del sistema profesional de compras y riesgo crediticio."""

from __future__ import annotations

import csv
import os
from datetime import date
from io import StringIO
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from modules.analisis import build_dashboard, parse_date
from modules.gestion import (
    create_purchase,
    create_supplier,
    list_purchases,
    list_suppliers,
    get_supplier_history,
    set_purchase_state,
    set_supplier_state,
    update_purchase,
    update_supplier,
)
from modules.inventario import (
    build_inventory_dashboard,
    create_inventory_movement,
    list_inventory,
    list_inventory_movements,
)
from modules.evaluacion import (
    build_evaluation_summary,
    build_operational_metrics,
    create_evaluation,
    list_evaluations,
)
from modules.qa import run_quality_assurance
from modules.proceso import (
    add_followup,
    add_incident,
    add_negotiation,
    add_quote,
    add_reception,
    compare_quotes,
    close_process,
    closure_checklist,
    create_order_from_process,
    create_payment_obligation,
    create_process,
    get_process,
    list_processes,
    register_payment,
    select_quote,
    set_process_state,
    update_incident,
    update_process,
)
from modules.storage import StorageError


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))


@app.errorhandler(StorageError)
def manejar_error_persistencia(error: StorageError):
    """Traduce fallas de lectura o escritura JSON a una respuesta API legible."""

    return jsonify({"error": str(error)}), 400


def _reference_date_from_request() -> date:
    value = request.args.get("fecha_corte", "").strip()
    if not value:
        return date.today()
    try:
        return parse_date(value)
    except ValueError as error:
        raise ValueError("fecha_corte debe tener formato AAAA-MM-DD.") from error


@app.route("/")
def index() -> str:
    return render_template("index.html", active_page="dashboard")


@app.route("/compras")
def compras() -> str:
    return render_template("compras.html", active_page="compras")


@app.route("/proveedores")
def proveedores() -> str:
    return render_template("proveedores.html", active_page="proveedores")


@app.route("/proveedores/<int:supplier_id>")
def proveedor_detalle(supplier_id: int) -> str:
    return render_template("proveedor_detalle.html", active_page="proveedores", supplier_id=supplier_id)


@app.route("/inventario")
def inventario() -> str:
    return render_template("inventario.html", active_page="inventario")


@app.route("/procesos")
def procesos() -> str:
    return render_template("procesos.html", active_page="procesos")


@app.route("/procesos/<int:process_id>")
def proceso_detalle(process_id: int) -> str:
    return render_template("proceso_detalle.html", active_page="procesos", process_id=process_id)


@app.route("/evaluacion")
def evaluacion() -> str:
    return render_template("evaluacion.html", active_page="evaluacion")


@app.route("/buscar")
def buscar() -> str:
    return render_template("buscar.html", active_page="", query=request.args.get("q", ""))


@app.route("/api/dashboard")
def api_dashboard():
    try:
        reference_date = _reference_date_from_request()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(build_dashboard(reference_date=reference_date))


@app.route("/api/inventario")
def api_inventario():
    try:
        reference_date = _reference_date_from_request()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(build_inventory_dashboard(reference_date=reference_date))


@app.route("/api/inventario/movimientos", methods=["GET", "POST"])
def api_inventario_movimientos():
    if request.method == "GET":
        return jsonify(
            {
                "movimientos": list_inventory_movements(
                    sku=request.args.get("sku", "")
                )
            }
        )

    payload = request.get_json(silent=True) or {}
    try:
        movement = create_inventory_movement(payload, reference_date=date.today())
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return (
        jsonify(
            {
                "message": "Movimiento de inventario registrado correctamente.",
                "movimiento": movement,
            }
        ),
        201,
    )


@app.route("/api/qa")
def api_qa():
    try:
        reference_date = _reference_date_from_request()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(run_quality_assurance(reference_date=reference_date))


@app.route("/api/evaluacion", methods=["GET", "POST"])
def api_evaluacion():
    if request.method == "GET":
        records = list_evaluations(
            task=request.args.get("tarea", ""),
            method=request.args.get("metodo", ""),
        )
        return jsonify({"evaluaciones": records, "resumen": build_evaluation_summary(records)})
    try:
        evaluation = create_evaluation(request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Medición registrada correctamente.", "evaluacion": evaluation}), 201


def _csv_download(filename: str, rows: list[dict[str, object]]) -> Response:
    output = StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    response = Response("\ufeff" + output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/api/exportar/metricas.csv")
def exportar_metricas():
    try:
        reference_date = _reference_date_from_request()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return _csv_download("metricas_compras.csv", build_operational_metrics(reference_date))


@app.route("/api/exportar/evaluacion.csv")
def exportar_evaluacion():
    summary = build_evaluation_summary()
    return _csv_download("evaluacion_antes_despues.csv", summary["comparaciones"])


@app.route("/api/busqueda")
def api_busqueda():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"error": "Escribe al menos 2 caracteres para buscar."}), 400
    inventory_query = query.casefold()
    inventory = [
        item for item in list_inventory()
        if inventory_query in str(item.get("sku", "")).casefold()
        or inventory_query in str(item.get("descripcion", "")).casefold()
    ]
    return jsonify({
        "consulta": query,
        "procesos": list_processes(query=query),
        "proveedores": list_suppliers(query=query),
        "ordenes": list_purchases(query=query),
        "inventario": inventory,
    })


@app.route("/api/proveedores", methods=["GET", "POST"])
def api_proveedores():
    if request.method == "GET":
        return jsonify(
            {
                "proveedores": list_suppliers(
                    query=request.args.get("q", ""),
                    state=request.args.get("estado", ""),
                )
            }
        )

    payload = request.get_json(silent=True) or {}
    try:
        supplier = create_supplier(payload)
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return (
        jsonify(
            {
                "message": "Proveedor agregado correctamente.",
                "proveedor": supplier,
            }
        ),
        201,
    )


@app.route("/api/proveedores/<int:supplier_id>", methods=["PUT"])
def api_proveedor_detail(supplier_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        supplier = update_supplier(supplier_id, payload)
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"message": "Proveedor actualizado correctamente.", "proveedor": supplier})


@app.route("/api/proveedores/<int:supplier_id>/estado", methods=["PATCH"])
def api_proveedor_estado(supplier_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        supplier = set_supplier_state(supplier_id, payload.get("estado"))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"message": "Estado del proveedor actualizado.", "proveedor": supplier})


@app.route("/api/proveedores/<int:supplier_id>/historial")
def api_proveedor_historial(supplier_id: int):
    try:
        return jsonify(get_supplier_history(supplier_id))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/procesos", methods=["GET", "POST"])
def api_procesos():
    if request.method == "GET":
        try:
            processes = list_processes(
                query=request.args.get("q", ""),
                state=request.args.get("estado", ""),
                priority=request.args.get("prioridad", ""),
                supplier_id=request.args.get("proveedor_id", ""),
                start_date=request.args.get("desde", ""),
                end_date=request.args.get("hasta", ""),
            )
        except (ValueError, StorageError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"procesos": processes})

    try:
        process = create_process(request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Proceso de compra creado correctamente.", "proceso": process}), 201


@app.route("/api/procesos/<int:process_id>", methods=["GET", "PUT"])
def api_proceso_detail(process_id: int):
    try:
        if request.method == "GET":
            return jsonify({"proceso": get_process(process_id)})
        process = update_process(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Proceso actualizado correctamente.", "proceso": process})


@app.route("/api/procesos/<int:process_id>/estado", methods=["PATCH"])
def api_proceso_estado(process_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        process = set_process_state(process_id, payload.get("estado"), payload.get("comentario", ""))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Estado del proceso actualizado.", "proceso": process})


@app.route("/api/procesos/<int:process_id>/cerrar", methods=["POST"])
def api_cerrar_proceso(process_id: int):
    payload = request.get_json(silent=True) or {}
    payment_applies = payload.get("pago_aplica", True)
    if isinstance(payment_applies, str):
        payment_applies = payment_applies.casefold() not in {"false", "0", "no"}
    try:
        process = close_process(process_id, bool(payment_applies))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Expediente cerrado correctamente.", "proceso": process})


@app.route("/api/procesos/<int:process_id>/cierre")
def api_checklist_cierre(process_id: int):
    value = request.args.get("pago_aplica", "true").casefold()
    payment_applies = value not in {"false", "0", "no"}
    try:
        return jsonify(closure_checklist(process_id, payment_applies))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/procesos/<int:process_id>/cotizaciones", methods=["GET", "POST"])
def api_proceso_cotizaciones(process_id: int):
    if request.method == "GET":
        try:
            comparison = compare_quotes(process_id)
        except (ValueError, StorageError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(comparison)
    try:
        quote = add_quote(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Cotización agregada correctamente.", "cotizacion": quote}), 201


@app.route("/api/procesos/<int:process_id>/cotizaciones/<int:quote_id>/seleccionar", methods=["POST"])
def api_proceso_seleccionar_cotizacion(process_id: int, quote_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        quote = select_quote(process_id, quote_id, payload.get("justificacion", ""))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Proveedor seleccionado correctamente.", "cotizacion": quote})


@app.route("/api/procesos/<int:process_id>/negociaciones", methods=["POST"])
def api_proceso_negociaciones(process_id: int):
    try:
        negotiation = add_negotiation(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Negociación registrada correctamente.", "negociacion": negotiation}), 201


@app.route("/api/procesos/<int:process_id>/orden", methods=["POST"])
def api_proceso_orden(process_id: int):
    try:
        order = create_order_from_process(process_id)
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Orden generada desde el proceso.", "compra": order}), 201


@app.route("/api/procesos/<int:process_id>/seguimiento", methods=["POST"])
def api_proceso_seguimiento(process_id: int):
    try:
        event = add_followup(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Seguimiento registrado correctamente.", "evento": event}), 201


@app.route("/api/procesos/<int:process_id>/incidencias", methods=["POST"])
def api_proceso_incidencia(process_id: int):
    try:
        incident = add_incident(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Incidencia registrada correctamente.", "incidencia": incident}), 201


@app.route("/api/procesos/<int:process_id>/recepciones", methods=["POST"])
def api_proceso_recepcion(process_id: int):
    try:
        reception = add_reception(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Recepción registrada y existencias actualizadas.", "recepcion": reception}), 201


@app.route("/api/procesos/<int:process_id>/pagos", methods=["POST"])
def api_proceso_pago(process_id: int):
    try:
        payment = create_payment_obligation(process_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Obligación de pago registrada correctamente.", "pago": payment}), 201


@app.route("/api/pagos/<int:payment_id>/aplicar", methods=["POST"])
def api_aplicar_pago(payment_id: int):
    try:
        payment = register_payment(payment_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Pago aplicado correctamente.", **payment}), 201


@app.route("/api/incidencias/<int:incident_id>/estado", methods=["PATCH"])
def api_actualizar_estado_incidencia(incident_id: int):
    try:
        incident = update_incident(incident_id, request.get_json(silent=True) or {})
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"message": "Incidencia actualizada correctamente.", "incidencia": incident})


@app.route("/api/compras", methods=["GET", "POST"])
def api_compras():
    if request.method == "GET":
        try:
            reference_date = _reference_date_from_request()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        try:
            purchases = list_purchases(
                reference_date=reference_date,
                query=request.args.get("q", ""),
                state=request.args.get("estado", ""),
                supplier_id=request.args.get("proveedor_id", ""),
                start_date=request.args.get("desde", ""),
                end_date=request.args.get("hasta", ""),
            )
        except (ValueError, StorageError) as error:
            return jsonify({"error": str(error)}), 400
        overdue_count = sum(
            1 for purchase in purchases if purchase["estado_credito"] == "Vencida"
        )
        total_amount = round(
            sum(purchase["monto_total"] for purchase in purchases),
            2,
        )
        return jsonify(
            {
                "fecha_corte": reference_date.isoformat(),
                "resumen": {
                    "compras": len(purchases),
                    "vigentes": len(purchases) - overdue_count,
                    "vencidas": overdue_count,
                    "monto_total": total_amount,
                    "por_estado": {
                        state: sum(1 for purchase in purchases if purchase["estado"] == state)
                        for state in {purchase["estado"] for purchase in purchases}
                    },
                },
                "compras": purchases,
            }
        )

    payload = request.get_json(silent=True) or {}
    try:
        purchase = create_purchase(payload)
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return (
        jsonify(
            {
                "message": "Compra agregada correctamente.",
                "compra": purchase,
            }
        ),
        201,
    )


@app.route("/api/compras/<int:purchase_id>", methods=["PUT"])
def api_compra_detail(purchase_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        purchase = update_purchase(purchase_id, payload)
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"message": "Orden actualizada correctamente.", "compra": purchase})


@app.route("/api/compras/<int:purchase_id>/estado", methods=["PATCH"])
def api_compra_estado(purchase_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        purchase = set_purchase_state(purchase_id, payload.get("estado"))
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"message": "Estado de la orden actualizado.", "compra": purchase})


if __name__ == "__main__":
    # Evita que la recarga automática bloquee el arranque en algunos entornos.
    # En macOS el puerto 5000 suele estar reservado por AirPlay Receiver.
    # Puede cambiarse con PORT=5000 (u otro puerto) si se requiere.
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=False, use_reloader=False, host="127.0.0.1", port=port)
