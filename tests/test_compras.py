import unittest
from datetime import date
from unittest.mock import patch

from modules.gestion import create_purchase, list_purchases, set_purchase_state


class PurchaseManagementTests(unittest.TestCase):
    def payload(self):
        return {
            "proveedor_id": 1,
            "fecha_orden": "2026-08-20",
            "dias_credito": 30,
            "impuestos": "4",
            "estado": "Emitida",
            "items": [
                {"sku": "A-1", "descripcion": "Producto A", "cantidad": "2", "precio_unitario": "10"},
                {"sku": "B-1", "descripcion": "Producto B", "cantidad": "1", "precio_unitario": "5"},
            ],
        }

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    @patch("modules.gestion.load_purchases")
    def test_create_purchase_calculates_totals_from_items(self, load_purchases, load_suppliers, write_json_file):
        load_purchases.return_value = []
        load_suppliers.return_value = [{"id": 1, "nombre": "Proveedor", "estado": "Activo", "dias_credito": 30}]

        purchase = create_purchase(self.payload())

        self.assertEqual(purchase["numero_orden"], "OC-2026-0001")
        self.assertEqual(purchase["subtotal"], 25.0)
        self.assertEqual(purchase["impuestos"], 4.0)
        self.assertEqual(purchase["total"], 29.0)
        self.assertEqual(len(purchase["items"]), 2)
        write_json_file.assert_called_once()

    @patch("modules.gestion.load_purchases")
    @patch("modules.gestion.load_suppliers")
    def test_list_purchases_normalizes_legacy_record(self, load_suppliers, load_purchases):
        load_suppliers.return_value = [{"id": 1, "nombre": "Proveedor"}]
        load_purchases.return_value = [{
            "id": 1,
            "factura": "F-1",
            "proveedor_id": 1,
            "sku": "A-1",
            "descripcion": "Producto A",
            "fecha_compra": "2026-08-01",
            "dias_credito": 10,
            "monto_total": 100,
        }]

        purchase = list_purchases(reference_date=date(2026, 8, 21))[0]

        self.assertEqual(purchase["numero_orden"], "F-1")
        self.assertEqual(purchase["items"][0]["cantidad"], 1)
        self.assertEqual(purchase["total"], 100.0)
        self.assertEqual(purchase["estado"], "Sin definir")

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    @patch("modules.gestion.load_purchases")
    def test_change_purchase_state(self, load_purchases, load_suppliers, write_json_file):
        records = [{"id": 1, "proveedor_id": 1, "fecha_compra": "2026-08-20", "dias_credito": 30, "monto_total": 10}]
        load_purchases.return_value = records
        load_suppliers.return_value = [{"id": 1, "nombre": "Proveedor"}]

        purchase = set_purchase_state(1, "Recibida")

        self.assertEqual(purchase["estado"], "Recibida")
        write_json_file.assert_called_once()


if __name__ == "__main__":
    unittest.main()
