# Auditoría inicial: tesis frente al código

## Alcance y evidencia

Esta revisión contrasta el repositorio disponible con el documento de especificación entregado para esta tarea. No se encontró en el repositorio una copia de la tesis ni del Anexo A; por ello no es posible verificar literalmente los capítulos 2, 3, 4 y 5 ni el manual final. Los hallazgos que dependen del contenido de la tesis quedan sujetos a cotejo cuando se proporcione ese documento.

Se revisaron las rutas de `main.py`, los módulos de negocio, las plantillas, los documentos técnicos y los nombres de los archivos JSON y pruebas. Esta fase no modifica código, plantillas ni datos.

## Resultado

La estructura funcional descrita en el documento está ampliamente presente: existen las nueve vistas HTML, las rutas API del ciclo de compra, persistencia JSON por entidad, indicadores operativos sin score, evaluación sin datos inventados, e idempotencia para entradas de inventario desde recepción. Los siguientes puntos requieren atención o confirmación antes de declarar conformidad total.

| Severidad | Área | Hallazgo basado en el código | Evidencia / acción requerida |
|---|---|---|---|
| IMPORTANTE | Trazabilidad con la tesis | No se puede confirmar que interfaz, indicadores, rutas y manual coincidan exactamente con la tesis porque no están disponibles el documento de tesis ni su Anexo A. | Solicitar ambos documentos y completar la matriz literal de requisitos contra capítulos y secciones. |
| MODERADO | Errores de persistencia en API | Varias rutas de lectura no capturan `StorageError`; por ejemplo, `/api/dashboard`, `/api/inventario`, `/api/qa`, GET `/api/evaluacion`, GET `/api/compras` y algunas exportaciones pueden terminar en error HTTP 500 si falla la lectura JSON. El contrato del documento pide traducir errores de persistencia a JSON 400. | Añadir manejo uniforme y pruebas de `StorageError` al completar la fase de rutas. |
| MODERADO | Convención de idioma | Los módulos conservan nombres públicos en inglés, como `build_dashboard`, `create_supplier`, `add_reception` y `run_quality_assurance`, aunque el principio 9 pide nombres de funciones y variables en español. Renombrarlos podría romper las firmas públicas, también protegidas por el documento. | Mantener compatibilidad y acordar si la regla aplica solo al código nuevo; no renombrar durante esta auditoría. |
| MODERADO | Prueba con fecha fija | La suite tiene una falla en `test_payment_obligation_calculates_due_date`: usa factura del 20-ago-2026 con vencimiento 19-sep-2026, pero espera `pendiente`. Al 6-oct-2026 el código devuelve `vencido`, conforme a la regla de marcar vencidas las obligaciones cuyo vencimiento ya pasó. | En la fase de pruebas, ajustar el caso para fijar la fecha de referencia o usar fechas relativas, sin debilitar la regla de negocio. |
| MODERADO | Cierre de expediente | El checklist exigía que todas las obligaciones estuvieran pagadas. La especificación pide que el pago esté definido o marcado como no aplicable; no exige liquidar el saldo para cerrar. | Se ajustó el checklist para aceptar una obligación registrada. |
| MENOR | Historial y mediciones | El historial se entregaba en orden de almacenamiento, no ordenado por fecha; la tabla de mediciones omitía las observaciones capturadas. | Se ordenó el historial por fecha de creación e ID y se añadió la columna de observaciones. |
| MODERADO | Resolución de incidencias | La interfaz permitía registrar incidencias pero no cambiar su estado desde el expediente; esto impedía resolverlas en la UI y completar el checklist. | Se añadió actualización de estado/resolución por API e interfaz y se cubrió en el flujo HTTP integral. |
| MODERADO | Ajuste de inventario | La función asignaba `Incremento` si un ajuste llegaba sin dirección, a pesar del requisito de dirección explícita. | Ahora rechaza ajustes sin dirección válida y se añadió prueba de esa validación. |
| MENOR | Respuesta de aplicación de pago | `POST /api/pagos/<id>/aplicar` responde 201 con `message`, `pago` y `movimiento` al expandir el resultado de `register_payment`; no usa una clave singular llamada `aplicacion`. El documento no fija el nombre de esa clave, así que no se considera incumplimiento confirmado. | Confirmar el contrato esperado en el Anexo A o en la tesis antes de cambiarlo. |

## Comprobaciones de conformidad visibles

| Requisito | Estado observado | Evidencia |
|---|---|---|
| Vistas del manual | PRESENTES | `main.py` declara `/`, `/compras`, `/proveedores`, `/proveedores/<id>`, `/inventario`, `/procesos`, `/procesos/<id>`, `/evaluacion` y `/buscar`. Existen las nueve plantillas correspondientes. |
| Rutas API del ciclo de compra | PRESENTES | Se encontraron endpoints de proveedores, compras, procesos, cotizaciones, selección, negociación, orden, seguimiento, incidencias, recepciones, pagos, inventario, QA, evaluación, búsqueda y exportación. |
| Fecha de corte | PRESENTE | `_reference_date_from_request()` valida `fecha_corte` con mensaje `fecha_corte debe tener formato AAAA-MM-DD.`; la usan dashboard, inventario, QA y listado de compras. |
| Dashboard e indicadores pedidos | PRESENTES | `build_dashboard()` combina compras/proveedores con los indicadores de `build_process_indicators()`, incluidos procesos abiertos, por estado, incidencias, pagos vencidos/por vencer, órdenes retrasadas, recepciones parciales, procesos estancados, proveedores incompletos, inventario bajo y alertas. |
| Reglas sin score predictivo | CONFORME | `calculate_supplier_risk()` documenta que genera indicadores de exposición, no score; la decisión también está declarada en README y documentación de arquitectura. |
| Atención binaria | CONFORME | `classify_attention()` devuelve `Requiere atención` si hay compras vencidas y `Sin vencimientos` en caso contrario. |
| Idempotencia por origen en recepción | CONFORME | `add_reception()` crea movimiento con `origen_tipo=recepcion` y `origen_id`; `create_inventory_movement()` rechaza el mismo origen y SKU. |
| Evaluación antes/después | CONFORME EN CÓDIGO | `modules/evaluacion.py` calcula estadística descriptiva y deja reducción en `None` si falta una muestra o la media manual es cero; `data/evaluaciones.json` está vacío. No hay evidencia de porcentajes operativos registrados. |
| Exportación CSV con BOM | CONFORME | `_csv_download()` antepone `\ufeff` al contenido CSV. |
| Persistencia JSON independiente | CONFORME | `data/` conserva archivos por entidad; `docs/data-model.md` registra las relaciones y el límite de falta de transacciones multiarchivo. |
| Inventario rezagado | CONFORME | `build_inventory_dashboard()` clasifica como rezagado el inventario con 90 días o más sin movimiento. |
| Control de calidad con referencias | CONFORME EN ESTRUCTURA | `modules/qa.py` produce campos `registros_afectados` y `referencias_afectadas` para validaciones. |
| Suite automatizada | 30/31 | Hay ocho archivos de pruebas; una prueba de vencimiento falla porque la fecha fija del caso ya venció al ejecutarse la suite. |

## Interfaz observada

- `index.html` contiene tarjetas, proveedor con mayor monto vencido, alertas, seguimiento por proveedor y control de calidad.
- `procesos.html` contiene captura de necesidad y filtros de estado, prioridad, proveedor y rango de fechas.
- `proceso_detalle.html` contiene formularios y tablas para cotización, comparación, selección, negociación, orden, seguimiento, incidencias, recepción, pagos y cierre.
- Compras, proveedores, inventario, evaluación y búsqueda tienen plantillas separadas con los formularios/tablas descritos en la especificación.
- La comparación exacta con el Anexo A sigue sin poderse cerrar hasta recibir la tesis/manual.

## Decisiones técnicas revisadas

- No se encontró una base de datos relacional ni dependencia externa adicional a Flask en `requirements.txt`.
- La entrada automática por recepción conserva origen y SKU para evitar duplicados.
- Las mediciones se almacenan aparte y no hay un resultado antes/después capturado en `data/evaluaciones.json`.
- La aplicación no incorpora autenticación, según README y documentación técnica.
- Las validaciones de negocio se ejecutan en módulos antes de persistir; la persistencia JSON no ofrece transacciones atómicas entre archivos, limitación ya documentada.

## Correcciones aplicadas después de la auditoría

- Se agregó un manejador Flask para responder `StorageError` como JSON 400 en
  las rutas que no capturaban de forma local el error de persistencia.
- Se alineó el checklist de cierre con el requisito de pago definido o no
  aplicable; se puede cerrar con una obligación pendiente registrada.
- Se agregó actualización de incidencias desde el expediente con registro de
  estado/resolución en su historial.
- Los ajustes de inventario ahora rechazan la falta de dirección explícita.
- El historial de eventos ahora se ordena por `created_at` e ID.
- La tabla de mediciones muestra todos los campos registrados, incluidas las
  observaciones.
- Se amplió la suite con errores de persistencia, renderizado de vistas,
  idempotencia y dirección de ajustes, más un flujo de compra por API en
  almacenamiento temporal.
- La prueba de vencimiento usa fechas relativas para seguir siendo válida en
  futuras ejecuciones.
- Se preparó `docs/manual-uso.md` a partir de las plantillas actuales. Falta
  cotejarlo con el Anexo A real.

## Resultado de pruebas

Resultado inicial: 31 pruebas ejecutadas, 30 aprobadas y 1 fallida por la fecha
fija descrita arriba. El resultado final de la suite ampliada se documentará en
`docs/implementation-report.md` al concluir la verificación final.
