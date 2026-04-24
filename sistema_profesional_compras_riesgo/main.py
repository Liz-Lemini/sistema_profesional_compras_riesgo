"""Servidor Flask del sistema profesional de compras y riesgo crediticio."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from modules.analisis import build_dashboard
from modules.gestion import create_purchase, create_supplier, list_purchases, list_suppliers
from modules.inventario import build_inventory_dashboard
from modules.storage import StorageError


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))


@app.route("/")
def index() -> str:
    return render_template("index.html", active_page="dashboard")


@app.route("/compras")
def compras() -> str:
    return render_template("compras.html", active_page="compras")


@app.route("/proveedores")
def proveedores() -> str:
    return render_template("proveedores.html", active_page="proveedores")


@app.route("/inventario")
def inventario() -> str:
    return render_template("inventario.html", active_page="inventario")


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(build_dashboard())


@app.route("/api/inventario")
def api_inventario():
    return jsonify(build_inventory_dashboard(reference_date=date.today()))


@app.route("/api/proveedores", methods=["GET", "POST"])
def api_proveedores():
    if request.method == "GET":
        return jsonify({"proveedores": list_suppliers()})

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


@app.route("/api/compras", methods=["GET", "POST"])
def api_compras():
    if request.method == "GET":
        purchases = list_purchases(reference_date=date.today())
        overdue_count = sum(
            1 for purchase in purchases if purchase["estado_credito"] == "Vencida"
        )
        total_amount = round(
            sum(purchase["monto_total"] for purchase in purchases),
            2,
        )
        return jsonify(
            {
                "fecha_corte": date.today().isoformat(),
                "resumen": {
                    "compras": len(purchases),
                    "vigentes": len(purchases) - overdue_count,
                    "vencidas": overdue_count,
                    "monto_total": total_amount,
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


if __name__ == "__main__":
    app.run(debug=True)
