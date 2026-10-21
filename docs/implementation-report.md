# Reporte de implementación

## Estado inicial

El repositorio contenía un MVP en Flask con proveedores, compras, inventario,
indicadores de crédito y persistencia mediante archivos JSON. La revisión del
27 de agosto de 2026 encontró 3 proveedores, 6 compras y 4 registros de
inventario; los archivos del expediente integrado no tenían registros.

## Problemas atendidos

- Flujo de compras aislado y sin expediente central.
- Falta de relaciones entre necesidad, cotización, orden, recepción e inventario.
- Seguimiento e incidencias sin estructura común.
- Ausencia de evaluación antes/después y exportación de evidencia.
- Búsqueda global y filtros operativos insuficientes.
- Cierre sin lista de verificación.
- QA sin validación de las entidades nuevas.

## Cambios

- Se consolidó `ProcesoCompra` con folio `PC-AAAA-NNNN`.
- Se agregaron cotizaciones, comparación transparente, selección justificada y
  negociación.
- La orden reutiliza los datos seleccionados y usa folio `OC-AAAA-NNNN`.
- Se agregaron seguimiento, estados de orden, incidencias, recepciones y
  entrada automática al inventario.
- Se agregaron obligaciones y aplicaciones de pago como seguimiento operativo.
- Se incorporaron cierre con checklist, historial de proveedor, búsqueda global,
  filtros, evaluación y exportaciones CSV.
- QA revisa duplicados, relaciones, totales, fechas, recepciones y saldos.

## Persistencia y migraciones

No se realizó migración a SQL. Se conservaron los archivos JSON y los registros
heredados. Los nuevos archivos se inicializan vacíos; no contienen resultados
ni datos empresariales inventados.

## Validación

La suite automatizada cubre validaciones, cálculos, transiciones, idempotencia,
recepción, pagos, evaluación, API y regresión. La aplicación también fue
levantada desde el repositorio objetivo y sus rutas principales respondieron
correctamente por HTTP.

## Limitaciones y pendientes

- Las mediciones antes/después deben levantarse con personal y operaciones reales.
- JSON no ofrece transacciones multiarchivo; se mantiene la idempotencia y QA.
- Pagos no sustituyen contabilidad ni conciliación bancaria.
- No hay autenticación; el uso previsto es local.
- No se implementan pronósticos ni score de proveedores.

## Estado final del sistema

La auditoría quedó registrada en `docs/audit-tesis-vs-codigo.md`. La
especificación entregada se cumple en la estructura funcional del proyecto:
Flask conserva la persistencia JSON y las rutas existentes; el ciclo cubre
necesidad, cotización, selección justificada, negociación, orden, seguimiento,
recepción, inventario, incidencias, pagos y cierre. No se añadió score
predictivo ni se inventaron resultados antes/después.

Correcciones aplicadas tras la auditoría:

- Las excepciones `StorageError` que llegan a Flask responden JSON con código
  400.
- El checklist considera definido un pago cuando existe una obligación
  registrada, o cuando se indica que no aplica; no exige que el saldo esté
  liquidado para cerrar.
- Se agregó una ruta PATCH para actualizar el estado y la resolución de una
  incidencia, con acceso desde el detalle del expediente.
- Un ajuste de inventario requiere dirección explícita y válida.
- El historial de eventos y la tabla de mediciones ahora muestran la
  información requerida en orden y con los campos capturados.
- Se actualizó README, documentación técnica y se agregó `docs/manual-uso.md`.

Verificación final ejecutada el 6 de octubre de 2026:

- `./.venv/bin/python -m unittest discover -s tests -v`: **37 pruebas,
  aprobadas**.
- El servidor se inició con `./.venv/bin/python main.py`; una solicitud HTTP a
  `http://127.0.0.1:5001/` respondió **200**. Las nueve vistas también
  respondieron 200 con el cliente de pruebas.
- `tests/test_end_to_end.py` recorrió por API un ciclo de compra en un
  directorio temporal, incluida resolución de incidencia, recepción, pagos,
  búsqueda, dashboard y exportación UTF-8 con BOM.

Pendiente documental para cotejo literal: el repositorio y el material recibido
no contienen la tesis ni el Anexo A. El manual generado refleja las plantillas
actuales, pero su equivalencia palabra por palabra con el anexo requiere esos
documentos. El árbol de trabajo de esta entrega no incluye datos nuevos de
operación ni mediciones comparativas.
