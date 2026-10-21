import unittest
from unittest.mock import patch

import main
from modules.storage import StorageError


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.testing = True
        cls.client = main.app.test_client()

    def test_accepts_reproducible_reference_date(self):
        for path in ("/api/dashboard", "/api/compras", "/api/inventario", "/api/qa"):
            response = self.client.get(f"{path}?fecha_corte=2026-08-21")
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.get_json()["fecha_corte" if path != "/api/qa" else "fecha_revision"], "2026-08-21")

    def test_rejects_invalid_reference_date(self):
        for path in ("/api/dashboard", "/api/compras", "/api/inventario", "/api/qa"):
            response = self.client.get(f"{path}?fecha_corte=21-08-2026")
            self.assertEqual(response.status_code, 400, path)
            self.assertEqual(response.get_json(), {"error": "fecha_corte debe tener formato AAAA-MM-DD."})

    def test_translates_storage_errors_to_json_400(self):
        with patch("main.build_dashboard", side_effect=StorageError("No fue posible leer 'compras.json'.")):
            response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "No fue posible leer 'compras.json'."})

    def test_all_html_views_render(self):
        for path in ("/", "/compras", "/proveedores", "/proveedores/1", "/inventario", "/procesos", "/procesos/1", "/evaluacion", "/buscar?q=ac"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_exposes_integrated_purchase_process_routes(self):
        for path in ("/procesos", "/api/procesos"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
        detail = self.client.get("/api/procesos/999999")
        self.assertEqual(detail.status_code, 400)

    def test_exposes_evaluation_search_and_exports(self):
        for path in ("/evaluacion", "/buscar?q=ac", "/api/evaluacion", "/api/busqueda?q=ac", "/api/exportar/metricas.csv", "/api/exportar/evaluacion.csv"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
        self.assertIn("text/csv", self.client.get("/api/exportar/metricas.csv").content_type)


if __name__ == "__main__":
    unittest.main()
