import unittest
from datetime import date
from unittest.mock import patch

from modules.qa import run_quality_assurance


class QualityAssuranceTests(unittest.TestCase):
    @patch("modules.qa.read_json_file")
    def test_reports_references_for_incomplete_supplier_records(self, read_json_file):
        data = {
            "proveedores.json": [{"id": 7, "nombre": "Proveedor incompleto"}],
            "compras.json": [],
            "inventario.json": [],
            "movimientos_inventario.json": [],
            "procesos_compra.json": [],
            "cotizaciones.json": [],
            "negociaciones.json": [],
            "seguimientos_compra.json": [],
            "incidencias.json": [],
            "recepciones.json": [],
            "pagos.json": [],
            "pagos_aplicados.json": [],
        }
        read_json_file.side_effect = lambda filename, default_data=None: data[filename]

        report = run_quality_assurance(date(2026, 8, 21))

        check = next(
            item
            for item in report["validaciones"]
            if item["nombre"] == "Datos obligatorios de proveedores"
        )
        self.assertEqual(
            check["referencias_afectadas"],
            [{"id": 7, "referencia": "Proveedor incompleto"}],
        )

    @patch("modules.qa.read_json_file")
    def test_detects_inconsistent_order_totals(self, read_json_file):
        data = {
            "proveedores.json": [{
                "id": 1,
                "nombre": "Proveedor",
                "asesor": "Ana",
                "telefono": "5512345678",
                "dias_credito": 30,
            }],
            "compras.json": [{
                "id": 1,
                "factura": "F-1",
                "proveedor_id": 1,
                "fecha_compra": "2026-08-20",
                "dias_credito": 30,
                "items": [{"sku": "A", "descripcion": "Producto", "cantidad": 2, "precio_unitario": 10}],
                "impuestos": 0,
                "total": 99,
                "estado": "Emitida",
            }],
            "inventario.json": [],
            "movimientos_inventario.json": [],
            "procesos_compra.json": [],
            "cotizaciones.json": [],
            "negociaciones.json": [],
            "seguimientos_compra.json": [],
            "incidencias.json": [],
            "recepciones.json": [],
            "pagos.json": [],
            "pagos_aplicados.json": [],
        }
        read_json_file.side_effect = lambda filename, default_data=None: data[filename]

        report = run_quality_assurance(date(2026, 8, 21))

        totals_check = next(item for item in report["validaciones"] if item["nombre"] == "Totales de órdenes consistentes")
        self.assertEqual(totals_check["estado"], "Requiere atención")
        self.assertEqual(totals_check["registros_afectados"], 1)


if __name__ == "__main__":
    unittest.main()
