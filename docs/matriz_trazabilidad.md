# Matriz de trazabilidad del proyecto

Esta matriz relaciona los objetivos académicos con lo que realmente existe en
el sistema. Las métricas marcadas como `por levantar` requieren mediciones del
proceso operativo; el código no inventa valores anteriores ni posteriores.
La tesis completa y el Anexo A no están incluidos en el repositorio disponible;
la correspondencia literal por capítulo debe confirmarse contra esos
documentos antes de declarar equivalencia textual.

| Objetivo | Requerimiento | Funcionalidad implementada | Módulo / archivo | Prueba | Evidencia | Métrica |
|---|---|---|---|---|---|---|
| Diagnosticar la gestión de información | Identificar campos incompletos, duplicados y relaciones inválidas | Revisión automática de proveedores, compras, inventario y movimientos, con referencias de los registros afectados | `modules/qa.py`, `/api/qa` | `tests/test_qa.py` | Respuesta JSON de QA y captura del reporte | Registros con observaciones; porcentaje de proveedores completos |
| Desarrollar una herramienta para proveedores | Registrar, consultar, buscar y modificar proveedores | Alta, edición, búsqueda por texto y filtro por estado | `modules/gestion.py`, `templates/proveedores.html` | `tests/test_gestion.py` | Registro JSON, formulario y tabla de proveedores | Tiempo de localización y registro: por levantar |
| Mejorar consistencia y trazabilidad | Conservar identificador, fecha, estado y relaciones | Proveedores con estado; órdenes con proveedor, fechas, partidas y estado; movimientos con SKU, fecha y tipo | `modules/gestion.py`, `modules/inventario.py` | `tests/test_compras.py`, `tests/test_inventario.py` | Registros JSON y detalle mostrado en pantalla | Porcentaje de registros con campos trazables |
| Gestionar compras | Capturar partidas y calcular totales de forma consistente | Órdenes con múltiples partidas, subtotal, impuestos, total y estados | `modules/gestion.py`, `templates/compras.html` | `tests/test_compras.py` | Orden registrada y resultado de QA de totales | Órdenes con totales consistentes; tiempo de captura: por levantar |
| Gestionar el proceso completo | Relacionar necesidad, cotizaciones, decisión, orden y resolución de incidencias | Expediente `PC-AAAA-NNNN`, comparación, selección justificada, negociación, orden, seguimiento, recepción, pagos, resolución de incidencia y cierre | `modules/proceso.py`, `main.py`, `templates/procesos.html`, `templates/proceso_detalle.html` | `tests/test_proceso.py`, `tests/test_end_to_end.py` | Expediente JSON, cotizaciones, eventos, incidencias y orden relacionada | Tiempo de seguimiento y porcentaje de operaciones trazables: por levantar |
| Gestionar existencias | Registrar entradas, salidas y ajustes sin existencia negativa | Movimiento de inventario y entrada automática desde recepción aceptada | `modules/inventario.py`, `modules/proceso.py`, `templates/inventario.html` | `tests/test_inventario.py`, `tests/test_proceso.py` | `data/movimientos_inventario.json`, recepción y existencia resultante | Movimientos válidos; salidas rechazadas; recepciones trazables |
| Gestionar pagos operativos | Conservar obligación, vencimiento, aplicaciones y saldo | Registro de obligación y pagos parciales/completos | `modules/proceso.py`, `templates/proceso_detalle.html` | `tests/test_proceso.py` | `data/pagos.json`, `data/pagos_aplicados.json` | Saldos consistentes; tiempo de conciliación: por levantar |
| Convertir datos en información útil | Calcular indicadores reproducibles | Dashboard de vencimientos, procesos abiertos, incidencias y pagos vencidos | `modules/analisis.py`, `modules/inventario.py`, `templates/index.html` | `tests/test_analisis.py`, `tests/test_inventario.py` | Respuestas de `/api/dashboard` y `/api/inventario` | Monto vencido, compras vencidas, procesos abiertos, alertas e inventario rezagado |
| Evaluar la herramienta | Verificar funcionamiento y regresión | Suite automatizada y comprobación de rutas principales | `tests/`, `main.py` | `python -m unittest discover -s tests -v` | Salida de pruebas y códigos HTTP | Casos aprobados / casos ejecutados; tiempos y errores del proceso: por levantar |
| Documentar y transferir conocimiento | Explicar instalación, alcance, datos, operación y pruebas | README, manual, matriz y definición de indicadores | `README.md`, `docs/manual-uso.md`, `docs/matriz_trazabilidad.md` | Revisión documental y suite | Archivos de documentación y procedimiento de ejecución | Reproducción de instalación y ejecución por verificar con usuario |

## Indicadores implementados

| Indicador | Fuente | Cálculo | Interpretación |
|---|---|---|---|
| Días restantes de crédito | Fecha de orden/compra, días de crédito y fecha de corte | `días de crédito - (fecha de corte - fecha de compra)` | Menor que cero significa que el plazo está vencido |
| Frecuencia de vencimiento | Órdenes del proveedor | `órdenes vencidas / órdenes totales × 100` | Proporción de órdenes vencidas dentro del conjunto registrado |
| Monto vencido | Monto de cada compra y días restantes | Suma de montos con días restantes menores que cero | Importe registrado que requiere seguimiento por vencimiento |
| Inventario rezagado | Días sin movimiento | Conteo de artículos con `días sin movimiento >= 90` | Artículos que requieren revisión de movimiento o uso |
| Capital inmovilizado | Stock actual y valor unitario de artículos rezagados | `stock actual × valor unitario` | Valor calculado del stock rezagado |
| Existencia baja | Stock actual y stock mínimo | Conteo de artículos con `stock actual <= stock mínimo` | Artículos que requieren revisión de abastecimiento |
| Procesos abiertos | Expedientes y estado | Conteo de procesos cuyo estado no es `completado` ni `cancelado` | Operaciones que todavía requieren seguimiento |
| Incidencias abiertas | Incidencias y estado | Conteo de incidencias `abierta` o `en_revision` | Casos operativos pendientes de resolución |
| Pagos vencidos | Fecha de vencimiento y saldo | Conteo de obligaciones con saldo positivo y vencimiento anterior a la fecha de corte | Obligaciones que requieren atención |

El sistema no calcula un score predictivo de proveedores ni un modelo
probabilístico. La clasificación `Requiere atención` se activa cuando existe al
menos una compra vencida y puede explicarse directamente con los registros.

## Mediciones operativas por levantar

Para evaluar la mejora frente al proceso anterior se debe registrar, en una
muestra definida y con el mismo criterio de medición:

- tiempo para localizar la información;
- tiempo de registro de proveedor u orden;
- número de pasos manuales;
- errores o correcciones detectadas;
- porcentaje de registros completos;
- porcentaje de operaciones con trazabilidad completa.

Las reducciones podrán calcularse posteriormente con:

```text
Reducción porcentual = (valor anterior - valor posterior) / valor anterior × 100
```

No se reportan resultados de reducción mientras esas mediciones no existan.
