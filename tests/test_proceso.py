import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from modules.proceso import (
    add_negotiation,
    add_followup,
    add_reception,
    add_quote,
    compare_quotes,
    create_payment_obligation,
    create_order_from_process,
    create_process,
    close_process,
    closure_checklist,
    get_process,
    register_payment,
    select_quote,
)
from modules.storage import read_json_file, write_json_file


class PurchaseProcessTests(unittest.TestCase):
    def process(self):
        return {
            "id": 1,
            "folio": "PC-2026-0001",
            "estado": "pendiente_cotizacion",
            "necesidad": "Producto de prueba",
            "prioridad": "Media",
        }

    @patch("modules.proceso.write_json_file")
    @patch("modules.proceso.load_events", return_value=[])
    @patch("modules.proceso.load_processes", return_value=[])
    def test_create_process_generates_folio_and_initial_state(self, load_processes, load_events, write_json_file):
        process = create_process({
            "necesidad": "Producto de prueba",
            "cantidad": "4",
            "prioridad": "Alta",
            "fecha_creacion": "2026-08-20",
        })

        self.assertEqual(process["folio"], "PC-2026-0001")
        self.assertEqual(process["estado"], "pendiente_cotizacion")
        self.assertEqual(process["cantidad"], 4)
        self.assertGreaterEqual(write_json_file.call_count, 2)

    @patch("modules.proceso.write_json_file")
    @patch("modules.proceso.load_events", return_value=[])
    @patch("modules.proceso.load_quotes", return_value=[])
    @patch("modules.proceso.load_processes")
    @patch("modules.proceso._supplier_map")
    def test_quote_calculates_structured_total(
        self,
        supplier_map,
        load_processes,
        load_quotes,
        load_events,
        write_json_file,
    ):
        load_processes.return_value = [self.process()]
        supplier_map.return_value = {3: {"id": 3, "nombre": "Proveedor", "estado": "Activo", "dias_credito": 30}}

        quote = add_quote(1, {
            "proveedor_id": 3,
            "sku": "SKU-1",
            "descripcion": "Producto",
            "cantidad": 2,
            "precio_unitario": 100,
            "envio": 20,
            "impuestos": 16,
            "dias_credito": 30,
            "plazo_entrega_dias": 5,
            "fecha": "2026-08-20",
        })

        self.assertEqual(quote["subtotal"], 200.0)
        self.assertEqual(quote["costo_total"], 236.0)
        self.assertEqual(load_processes.return_value[0]["estado"], "cotizando")

    @patch("modules.proceso._supplier_map", return_value={3: {"nombre": "Proveedor"}})
    @patch("modules.proceso.load_quotes")
    def test_compare_quotes_returns_transparent_highlights(self, load_quotes, supplier_map):
        load_quotes.return_value = [
            {"id": 1, "proceso_id": 1, "proveedor_id": 3, "costo_total": 200, "dias_credito": 15, "plazo_entrega_dias": 8},
            {"id": 2, "proceso_id": 1, "proveedor_id": 3, "costo_total": 240, "dias_credito": 30, "plazo_entrega_dias": 5},
        ]

        result = compare_quotes(1)

        self.assertEqual(result["destacados"], {
            "menor_costo_total": 1,
            "mayor_credito": 2,
            "menor_plazo_entrega": 2,
        })

    @patch("modules.proceso.write_json_file")
    @patch("modules.proceso._append_event")
    @patch("modules.proceso.load_quotes")
    @patch("modules.proceso.load_processes")
    def test_selection_requires_justification(self, load_processes, load_quotes, append_event, write_json_file):
        load_processes.return_value = [self.process()]
        load_quotes.return_value = [{"id": 5, "proceso_id": 1, "proveedor_id": 3, "seleccionada": False}]

        with self.assertRaises(ValueError):
            select_quote(1, 5, "")

        selected = select_quote(1, 5, "Menor costo total y plazo aceptable")

        self.assertEqual(selected["id"], 5)
        self.assertEqual(load_processes.return_value[0]["estado"], "proveedor_seleccionado")
        self.assertEqual(load_processes.return_value[0]["justificacion_seleccion"], "Menor costo total y plazo aceptable")

    @patch("modules.gestion.create_purchase")
    @patch("modules.proceso.write_json_file")
    @patch("modules.proceso._append_event")
    @patch("modules.proceso.load_negotiations", return_value=[])
    @patch("modules.proceso.load_quotes")
    @patch("modules.proceso.load_processes")
    def test_order_reuses_selected_quote(
        self,
        load_processes,
        load_quotes,
        load_negotiations,
        append_event,
        write_json_file,
        create_purchase,
    ):
        process = {**self.process(), "estado": "proveedor_seleccionado", "cotizacion_seleccionada_id": 5, "proveedor_id": 3}
        load_processes.return_value = [process]
        load_quotes.return_value = [{
            "id": 5,
            "proceso_id": 1,
            "proveedor_id": 3,
            "sku": "SKU-1",
            "descripcion": "Producto",
            "cantidad": 2,
            "precio_unitario": 100,
            "impuestos": 16,
            "dias_credito": 30,
            "plazo_entrega_dias": 5,
        }]
        create_purchase.return_value = {"id": 8, "numero_orden": "OC-2026-0008"}

        order = create_order_from_process(1)

        payload = create_purchase.call_args.args[0]
        self.assertEqual(order["id"], 8)
        self.assertEqual(payload["proceso_id"], 1)
        self.assertEqual(payload["items"][0]["precio_unitario"], 100)
        self.assertEqual(process["estado"], "orden_emitida")

    @patch("modules.proceso.load_processes")
    def test_order_generation_rejects_duplicate_link(self, load_processes):
        load_processes.return_value = [{**self.process(), "estado": "orden_emitida", "orden_id": 8}]

        with self.assertRaises(ValueError):
            create_order_from_process(1)

    @patch("modules.proceso._set_process_state")
    @patch("modules.inventario.create_inventory_movement")
    @patch("modules.proceso._read")
    @patch("modules.proceso.load_receipts", return_value=[])
    @patch("modules.proceso.load_processes")
    @patch("modules.proceso.write_json_file")
    def test_reception_generates_inventory_entry(
        self,
        write_json_file,
        load_processes,
        load_receipts,
        read_collection,
        create_inventory_movement,
        set_process_state,
    ):
        process = {**self.process(), "estado": "orden_emitida"}
        load_processes.return_value = [process]
        read_collection.return_value = [{
            "id": 8,
            "proceso_id": 1,
            "items": [{"sku": "SKU-1", "cantidad": 2}],
        }]
        create_inventory_movement.return_value = {"id": 1, "sku": "SKU-1", "stock_actual": 12}

        with patch("modules.inventario.load_inventory", return_value=[{"sku": "SKU-1"}]):
            reception = add_reception(1, {
                "orden_id": 8,
                "fecha": "2026-08-20",
                "items": [{"sku": "SKU-1", "cantidad_recibida": 2, "cantidad_aceptada": 2, "cantidad_rechazada": 0}],
            })

        self.assertEqual(reception["estado"], "recibido")
        self.assertEqual(len(reception["movimientos_inventario"]), 1)
        movement_payload = create_inventory_movement.call_args.args[0]
        self.assertEqual(movement_payload["origen_tipo"], "recepcion")
        self.assertEqual(movement_payload["origen_id"], reception["id"])

    @patch("modules.proceso._set_process_state")
    @patch("modules.proceso._process_order")
    @patch("modules.proceso.load_payments", return_value=[])
    @patch("modules.proceso.load_processes")
    @patch("modules.proceso.write_json_file")
    def test_payment_obligation_calculates_due_date(
        self,
        write_json_file,
        load_processes,
        load_payments,
        process_order,
        set_process_state,
    ):
        load_processes.return_value = [{**self.process(), "estado": "recibido"}]
        process_order.return_value = {"id": 8, "proceso_id": 1, "proveedor_id": 3, "total": 150, "dias_credito": 30}

        fecha_factura = date.today() - timedelta(days=10)
        fecha_vencimiento = fecha_factura + timedelta(days=30)
        payment = create_payment_obligation(1, {
            "orden_id": 8,
            "fecha_factura": fecha_factura.isoformat(),
            "dias_credito": 30,
        })

        self.assertEqual(payment["fecha_vencimiento"], fecha_vencimiento.isoformat())
        self.assertEqual(payment["saldo"], 150.0)
        self.assertEqual(payment["estado"], "pendiente")

    @patch("modules.proceso._set_process_state")
    @patch("modules.proceso.load_processes")
    @patch("modules.proceso.load_payment_movements", return_value=[])
    @patch("modules.proceso.load_payments")
    @patch("modules.proceso.write_json_file")
    def test_register_payment_updates_balance(
        self,
        write_json_file,
        load_payments,
        load_payment_movements,
        load_processes,
        set_process_state,
    ):
        payment = {"id": 2, "proceso_id": 1, "monto": 150.0, "monto_pagado": 0.0, "saldo": 150.0, "fecha_vencimiento": "2026-09-19", "estado": "pendiente"}
        load_payments.return_value = [payment]
        load_processes.return_value = [{**self.process(), "estado": "pendiente_pago"}]

        result = register_payment(2, {"monto": 50, "fecha": "2026-08-21"})

        self.assertEqual(result["pago"]["monto_pagado"], 50.0)
        self.assertEqual(result["pago"]["saldo"], 100.0)
        self.assertEqual(result["pago"]["estado"], "parcial")

    def test_full_purchase_cycle_is_traceable(self):
        with TemporaryDirectory() as directory, patch("modules.storage.DATA_DIR", Path(directory)):
            write_json_file("proveedores.json", [
                {"id": 1, "nombre": "Proveedor Uno", "asesor": "Ana", "telefono": "5512345678", "dias_credito": 30, "estado": "Activo"},
                {"id": 2, "nombre": "Proveedor Dos", "asesor": "Luis", "telefono": "5512345679", "dias_credito": 15, "estado": "Activo"},
            ])
            write_json_file("inventario.json", [{"id": 1, "sku": "SKU-1", "descripcion": "Producto", "stock_actual": 0, "stock_minimo": 1, "valor_unitario": 10, "dias_sin_movimiento": 0}])
            today = date.today().isoformat()

            process = create_process({"necesidad": "Producto de ciclo completo", "cantidad": 2, "fecha_creacion": today})
            add_quote(1, {"proveedor_id": 1, "sku": "SKU-1", "descripcion": "Producto", "cantidad": 2, "precio_unitario": 10, "fecha": today})
            second_quote = add_quote(1, {"proveedor_id": 2, "sku": "SKU-1", "descripcion": "Producto", "cantidad": 2, "precio_unitario": 11, "fecha": today})
            select_quote(1, 1, "Menor costo total")
            add_negotiation(1, {"cotizacion_id": 1, "precio_negociado": 9, "credito_negociado": 30, "plazo_negociado": 2, "fecha": today})
            order = create_order_from_process(1)
            add_followup(1, {"orden_id": order["id"], "tipo": "en_transito", "comentario": "Confirmado por proveedor"})
            reception = add_reception(1, {"orden_id": order["id"], "fecha": today, "items": [{"sku": "SKU-1", "cantidad_recibida": 2, "cantidad_aceptada": 2, "cantidad_rechazada": 0}]})
            payment = create_payment_obligation(1, {"orden_id": order["id"], "fecha_factura": today, "monto": order["total"]})
            register_payment(payment["id"], {"monto": order["total"], "fecha": today})
            closed = close_process(1, payment_applies=True)
            detail = get_process(1)

            self.assertEqual(process["folio"], "PC-" + today[:4] + "-0001")
            self.assertEqual(second_quote["proceso_id"], process["id"])
            self.assertEqual(reception["estado"], "recibido")
            self.assertEqual(closed["estado"], "completado")
            self.assertEqual(detail["resumen"]["cotizaciones"], 2)
            self.assertEqual(detail["resumen"]["ordenes"], 1)
            self.assertEqual(read_json_file("inventario.json")[0]["stock_actual"], 2)

    @patch("modules.proceso.load_payments", return_value=[{"id": 3, "proceso_id": 1, "estado": "pendiente"}])
    @patch("modules.proceso.load_incidents", return_value=[])
    @patch("modules.proceso.load_receipts", return_value=[{"id": 4, "proceso_id": 1, "estado": "recibido"}])
    @patch("modules.proceso._read", return_value=[{"id": 8, "proceso_id": 1}])
    @patch("modules.proceso.load_processes")
    def test_closure_accepts_defined_unpaid_obligation(
        self,
        load_processes,
        read_records,
        load_receipts,
        load_incidents,
        load_payments,
    ):
        load_processes.return_value = [{
            **self.process(),
            "proveedor_id": 3,
            "cotizacion_seleccionada_id": 5,
            "orden_id": 8,
        }]

        checklist = closure_checklist(1)

        self.assertTrue(checklist["puede_cerrar"])
        pago = next(item for item in checklist["validaciones"] if item["clave"] == "pago")
        self.assertTrue(pago["cumple"])


if __name__ == "__main__":
    unittest.main()
