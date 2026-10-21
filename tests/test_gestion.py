import unittest
from unittest.mock import patch

from modules.gestion import (
    create_supplier,
    list_suppliers,
    set_supplier_state,
    update_supplier,
)


class SupplierManagementTests(unittest.TestCase):
    def valid_payload(self):
        return {
            "nombre": "Proveedor de prueba",
            "asesor": "Ana López",
            "telefono": "5512345678",
            "dias_credito": "30",
            "correo": "ana@example.com",
            "sector": "Tecnología",
            "notas": "Sin observaciones",
        }

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    def test_create_supplier_requires_valid_phone(self, load_suppliers, write_json_file):
        load_suppliers.return_value = []
        payload = self.valid_payload()
        payload["telefono"] = "123"

        with self.assertRaises(ValueError):
            create_supplier(payload)

        write_json_file.assert_not_called()

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    def test_create_supplier_normalizes_and_returns_current_schema(self, load_suppliers, write_json_file):
        load_suppliers.return_value = []
        payload = self.valid_payload()
        payload["telefono"] = "55 1234-5678"

        supplier = create_supplier(payload)

        self.assertEqual(supplier["id"], 1)
        self.assertEqual(supplier["telefono"], "5512345678")
        self.assertEqual(supplier["estado"], "Activo")
        write_json_file.assert_called_once()

    @patch("modules.gestion.load_suppliers")
    def test_list_suppliers_supports_search_and_legacy_records(self, load_suppliers):
        load_suppliers.return_value = [
            {
                "id": 1,
                "nombre": "Proveedor Legacy",
                "contacto": "legacy@example.com",
            },
            {
                "id": 2,
                "nombre": "Otro Proveedor",
                "asesor": "Ana",
                "telefono": "5512345678",
                "dias_credito": 30,
                "estado": "Activo",
            },
        ]

        results = list_suppliers(query="legacy")

        self.assertEqual([item["id"] for item in results], [1])
        self.assertEqual(results[0]["estado"], "Pendiente")

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    def test_update_and_change_state(self, load_suppliers, write_json_file):
        records = [{"id": 1, "nombre": "Proveedor", "estado": "Activo"}]
        load_suppliers.return_value = records

        updated = update_supplier(1, self.valid_payload())
        self.assertEqual(updated["asesor"], "Ana López")

        changed = set_supplier_state(1, "Inactivo")
        self.assertEqual(changed["estado"], "Inactivo")
        self.assertGreaterEqual(write_json_file.call_count, 2)

    @patch("modules.gestion.write_json_file")
    @patch("modules.gestion.load_suppliers")
    def test_legacy_supplier_cannot_be_activated_before_completion(self, load_suppliers, write_json_file):
        load_suppliers.return_value = [{"id": 1, "nombre": "Legacy", "contacto": "legacy@example.com"}]

        with self.assertRaises(ValueError):
            set_supplier_state(1, "Activo")

        write_json_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
