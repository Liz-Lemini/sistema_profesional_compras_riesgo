import unittest
from datetime import date
from unittest.mock import patch

from modules.evaluacion import build_evaluation_summary, create_evaluation


class EvaluationTests(unittest.TestCase):
    @patch("modules.evaluacion.write_json_file")
    @patch("modules.evaluacion.load_evaluations", return_value=[])
    def test_create_evaluation_requires_real_validated_measurement(self, load_evaluations, write_json_file):
        evaluation = create_evaluation({
            "tarea": "buscar_proveedor",
            "metodo": "sistema",
            "fecha": date.today().isoformat(),
            "duracion_segundos": "12.5",
            "errores_detectados": "0",
        })

        self.assertEqual(evaluation["duracion_segundos"], 12.5)
        self.assertEqual(evaluation["errores_detectados"], 0)
        write_json_file.assert_called_once()

    def test_summary_reports_sample_sizes_and_reduction(self):
        records = [
            {"id": 1, "tarea": "generar_orden", "metodo": "manual", "duracion_segundos": 100, "errores_detectados": 1},
            {"id": 2, "tarea": "generar_orden", "metodo": "manual", "duracion_segundos": 80, "errores_detectados": 0},
            {"id": 3, "tarea": "generar_orden", "metodo": "sistema", "duracion_segundos": 50, "errores_detectados": 0},
        ]

        summary = build_evaluation_summary(records)
        comparison = next(item for item in summary["comparaciones"] if item["tarea"] == "generar_orden")

        self.assertEqual(comparison["manual_n"], 2)
        self.assertEqual(comparison["system_n"], 1)
        self.assertEqual(comparison["manual_mean_segundos"], 90.0)
        self.assertEqual(comparison["system_mean_segundos"], 50.0)
        self.assertEqual(comparison["reduccion_tiempo_pct"], 44.44)


if __name__ == "__main__":
    unittest.main()
