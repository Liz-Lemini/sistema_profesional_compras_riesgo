import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import main
from modules.storage import write_json_file


class PurchaseCycleApiTests(unittest.TestCase):
    def test_purchase_cycle_through_http_api(self):
        with TemporaryDirectory() as directory, patch("modules.storage.DATA_DIR", Path(directory)):
            write_json_file("inventario.json", [{
                "id": 1,
                "sku": "SKU-1",
                "descripcion": "Producto de prueba",
                "stock_actual": 0,
                "stock_minimo": 1,
                "valor_unitario": 10,
                "dias_sin_movimiento": 0,
            }])
            client = main.app.test_client()
            hoy = date.today().isoformat()

            proveedor_ids = []
            for nombre, telefono in (("Proveedor Uno", "5512345678"), ("Proveedor Dos", "5512345679")):
                response = client.post("/api/proveedores", json={
                    "nombre": nombre,
                    "asesor": "Agente de prueba",
                    "telefono": telefono,
                    "dias_credito": 15,
                    "correo": "compras@example.test",
                })
                self.assertEqual(response.status_code, 201, response.get_json())
                proveedor_ids.append(response.get_json()["proveedor"]["id"])

            response = client.post("/api/procesos", json={
                "necesidad": "Producto de prueba",
                "cantidad": 2,
                "prioridad": "Alta",
                "fecha_creacion": hoy,
            })
            self.assertEqual(response.status_code, 201, response.get_json())
            proceso_id = response.get_json()["proceso"]["id"]

            for proveedor_id, precio in zip(proveedor_ids, (10, 11)):
                response = client.post(f"/api/procesos/{proceso_id}/cotizaciones", json={
                    "proveedor_id": proveedor_id,
                    "sku": "SKU-1",
                    "descripcion": "Producto de prueba",
                    "cantidad": 2,
                    "precio_unitario": precio,
                    "envio": 0,
                    "impuestos": 0,
                    "dias_credito": 15,
                    "plazo_entrega_dias": 2,
                    "fecha": hoy,
                })
                self.assertEqual(response.status_code, 201, response.get_json())

            comparison = client.get(f"/api/procesos/{proceso_id}/cotizaciones")
            self.assertEqual(comparison.status_code, 200)
            quote_id = comparison.get_json()["destacados"]["menor_costo_total"]
            response = client.post(
                f"/api/procesos/{proceso_id}/cotizaciones/{quote_id}/seleccionar",
                json={"justificacion": "Menor costo total"},
            )
            self.assertEqual(response.status_code, 200)

            response = client.post(f"/api/procesos/{proceso_id}/negociaciones", json={
                "cotizacion_id": quote_id,
                "precio_negociado": 9,
                "credito_negociado": 15,
                "plazo_negociado": 2,
                "fecha": hoy,
            })
            self.assertEqual(response.status_code, 201, response.get_json())

            response = client.post(f"/api/procesos/{proceso_id}/orden", json={})
            self.assertEqual(response.status_code, 201, response.get_json())
            orden_id = response.get_json()["compra"]["id"]

            response = client.post(f"/api/procesos/{proceso_id}/seguimiento", json={
                "orden_id": orden_id,
                "tipo": "confirmacion",
                "fecha_estimada": hoy,
                "fecha_real": hoy,
                "comentario": "Confirmada",
            })
            self.assertEqual(response.status_code, 201, response.get_json())

            response = client.post(f"/api/procesos/{proceso_id}/recepciones", json={
                "orden_id": orden_id,
                "fecha": hoy,
                "items": [{
                    "sku": "SKU-1",
                    "cantidad_recibida": 2,
                    "cantidad_aceptada": 1,
                    "cantidad_rechazada": 1,
                }],
            })
            self.assertEqual(response.status_code, 201, response.get_json())
            incidencia_id = response.get_json()["recepcion"]["incidencia_sugerida"]["id"]
            response = client.patch(f"/api/incidencias/{incidencia_id}/estado", json={
                "estado": "resuelta",
                "resolucion": "La unidad dañada quedó identificada y documentada",
            })
            self.assertEqual(response.status_code, 200, response.get_json())

            response = client.post(f"/api/procesos/{proceso_id}/pagos", json={
                "orden_id": orden_id,
                "fecha_factura": hoy,
                "dias_credito": 0,
                "monto": 18,
            })
            self.assertEqual(response.status_code, 201, response.get_json())
            payment_id = response.get_json()["pago"]["id"]
            response = client.post(f"/api/pagos/{payment_id}/aplicar", json={"monto": 8, "fecha": hoy})
            self.assertEqual(response.status_code, 201, response.get_json())
            response = client.post(f"/api/pagos/{payment_id}/aplicar", json={"monto": 10, "fecha": hoy})
            self.assertEqual(response.status_code, 201, response.get_json())

            checklist = client.get(f"/api/procesos/{proceso_id}/cierre")
            self.assertEqual(checklist.status_code, 200)
            self.assertTrue(checklist.get_json()["puede_cerrar"])
            response = client.post(f"/api/procesos/{proceso_id}/cerrar", json={})
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.get_json()["proceso"]["estado"], "completado")

            dashboard = client.get("/api/dashboard")
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.get_json()["resumen"]["procesos_abiertos"], 0)
            self.assertIn("alertas", dashboard.get_json()["resumen"])
            self.assertEqual(client.get("/api/inventario").get_json()["inventario"][0]["stock_actual"], 1)
            search = client.get("/api/busqueda?q=SKU-1")
            self.assertEqual(search.status_code, 200)
            self.assertTrue(search.get_json()["ordenes"])
            self.assertTrue(search.get_json()["inventario"])
            export = client.get("/api/exportar/evaluacion.csv")
            self.assertEqual(export.status_code, 200)
            self.assertTrue(export.get_data().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
