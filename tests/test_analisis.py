import unittest
from datetime import date
from unittest.mock import patch

from modules.analisis import build_dashboard, calculate_supplier_risk


class OperationalIndicatorsTests(unittest.TestCase):
    def test_supplier_report_uses_traceable_overdue_indicators(self):
        supplier = {"id": 1, "nombre": "Proveedor"}
        purchases = [
            {
                "id": 1,
                "proveedor_id": 1,
                "factura": "F-1",
                "fecha_compra": "2026-08-01",
                "dias_credito": 10,
                "monto_total": 100,
            },
            {
                "id": 2,
                "proveedor_id": 1,
                "factura": "F-2",
                "fecha_compra": "2026-08-15",
                "dias_credito": 30,
                "monto_total": 50,
            },
        ]

        report = calculate_supplier_risk(supplier, purchases, date(2026, 8, 21))

        self.assertEqual(report["nivel_atencion"], "Requiere atención")
        self.assertEqual(report["metricas"]["facturas_vencidas"], 1)
        self.assertEqual(report["metricas"]["monto_vencido"], 100.0)
        self.assertEqual(report["metricas"]["dias_maximo_atraso"], 10)
        self.assertNotIn("score", report)

    @patch("modules.analisis.load_purchases")
    @patch("modules.analisis.load_suppliers")
    def test_dashboard_summary_aggregates_overdue_amount(self, load_suppliers, load_purchases):
        load_suppliers.return_value = [{"id": 1, "nombre": "Proveedor"}]
        load_purchases.return_value = [
            {
                "id": 1,
                "proveedor_id": 1,
                "factura": "F-1",
                "fecha_compra": "2026-08-01",
                "dias_credito": 10,
                "monto_total": 100,
            }
        ]

        summary = build_dashboard(date(2026, 8, 21))["resumen"]

        self.assertEqual(summary["compras"], 1)
        self.assertEqual(summary["compras_vencidas"], 1)
        self.assertEqual(summary["monto_vencido"], 100.0)


if __name__ == "__main__":
    unittest.main()
