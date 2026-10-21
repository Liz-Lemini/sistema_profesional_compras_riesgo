import unittest
from datetime import date
from unittest.mock import patch

from modules.inventario import build_inventory_dashboard, create_inventory_movement


class InventoryManagementTests(unittest.TestCase):
    @patch("modules.inventario.write_json_file")
    @patch("modules.inventario.load_inventory_movements")
    @patch("modules.inventario.load_inventory")
    def test_entry_updates_stock_and_creates_traceable_movement(
        self,
        load_inventory,
        load_movements,
        write_json_file,
    ):
        load_inventory.return_value = [
            {
                "id": 1,
                "sku": "SKU-1",
                "descripcion": "Producto",
                "stock_actual": 10,
                "stock_minimo": 4,
                "valor_unitario": 25,
                "dias_sin_movimiento": 90,
            }
        ]
        load_movements.return_value = []

        movement = create_inventory_movement(
            {
                "sku": "SKU-1",
                "tipo": "Entrada",
                "cantidad": "2",
                "fecha": "2026-08-20",
                "observaciones": "Recepción parcial",
            },
            reference_date=date(2026, 8, 21),
        )

        self.assertEqual(movement["id"], 1)
        self.assertEqual(movement["stock_actual"], 12)
        self.assertEqual(load_inventory.return_value[0]["stock_inicial"], 10)
        self.assertEqual(load_inventory.return_value[0]["stock_actual"], 12)
        self.assertEqual(write_json_file.call_count, 2)

    @patch("modules.inventario.write_json_file")
    @patch("modules.inventario.load_inventory_movements", return_value=[])
    @patch("modules.inventario.load_inventory")
    def test_exit_cannot_exceed_current_stock(self, load_inventory, load_movements, write_json_file):
        load_inventory.return_value = [{"sku": "SKU-1", "stock_actual": 3}]

        with self.assertRaises(ValueError):
            create_inventory_movement(
                {"sku": "SKU-1", "tipo": "Salida", "cantidad": 4},
                reference_date=date(2026, 8, 21),
            )

        write_json_file.assert_not_called()

    @patch("modules.inventario.write_json_file")
    @patch("modules.inventario.load_inventory_movements", return_value=[])
    @patch("modules.inventario.load_inventory")
    def test_adjustment_requires_direction_and_updates_stock(self, load_inventory, load_movements, write_json_file):
        load_inventory.return_value = [{"sku": "SKU-1", "stock_actual": 5}]

        with self.assertRaises(ValueError):
            create_inventory_movement(
                {"sku": "SKU-1", "tipo": "Ajuste", "cantidad": 2},
                reference_date=date.today(),
            )
        write_json_file.assert_not_called()

        movement = create_inventory_movement(
            {"sku": "SKU-1", "tipo": "Ajuste", "direccion": "Decremento", "cantidad": 2},
            reference_date=date.today(),
        )

        self.assertEqual(movement["direccion"], "Decremento")
        self.assertEqual(load_inventory.return_value[0]["stock_actual"], 3)

    @patch("modules.inventario.write_json_file")
    @patch("modules.inventario.load_inventory_movements")
    @patch("modules.inventario.load_inventory")
    def test_rejects_duplicate_origin_and_sku(self, load_inventory, load_movements, write_json_file):
        load_inventory.return_value = [{"sku": "SKU-1", "stock_actual": 5}]
        load_movements.return_value = [{"sku": "SKU-1", "origen_tipo": "recepcion", "origen_id": 9}]

        with self.assertRaisesRegex(ValueError, "Este origen ya generó"):
            create_inventory_movement({
                "sku": "SKU-1",
                "tipo": "Entrada",
                "cantidad": 2,
                "origen_tipo": "recepcion",
                "origen_id": 9,
            }, reference_date=date.today())

        write_json_file.assert_not_called()

    @patch("modules.inventario.load_inventory_movements", return_value=[])
    @patch("modules.inventario.load_inventory")
    def test_dashboard_marks_low_stock(self, load_inventory, load_movements):
        load_inventory.return_value = [
            {
                "sku": "SKU-1",
                "descripcion": "Producto",
                "stock_actual": 2,
                "stock_minimo": 3,
                "valor_unitario": 10,
                "dias_sin_movimiento": 0,
            }
        ]

        dashboard = build_inventory_dashboard(reference_date=date(2026, 8, 21))

        self.assertEqual(dashboard["resumen"]["inventario_bajo"], 1)
        self.assertTrue(dashboard["inventario"][0]["existencia_baja"])


if __name__ == "__main__":
    unittest.main()
