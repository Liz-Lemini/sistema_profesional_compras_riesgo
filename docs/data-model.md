# Modelo de datos JSON

La persistencia actual utiliza archivos JSON separados. Cada registro conserva
un identificador y las relaciones se expresan mediante campos como
`proceso_id`, `proveedor_id`, `orden_id` y `cotizacion_id`.

| Archivo | Entidad | Relación principal |
|---|---|---|
| `proveedores.json` | Proveedor | `id` |
| `compras.json` | Orden de compra | `proveedor_id`, `proceso_id` |
| `procesos_compra.json` | Proceso de compra | `id`, `folio` |
| `cotizaciones.json` | Cotización | `proceso_id`, `proveedor_id` |
| `negociaciones.json` | Negociación | `proceso_id`, `cotizacion_id` |
| `seguimientos_compra.json` | Evento de seguimiento | `proceso_id`, `orden_id` |
| `incidencias.json` | Incidencia | `proceso_id`, `orden_id`, `proveedor_id` |
| `recepciones.json` | Recepción | `proceso_id`, `orden_id` |
| `inventario.json` | Existencia | `sku` |
| `movimientos_inventario.json` | Movimiento | `sku`, `origen_tipo`, `origen_id` |
| `pagos.json` | Obligación de pago | `proceso_id`, `orden_id`, `proveedor_id` |
| `pagos_aplicados.json` | Aplicación de pago | `pago_id` |
| `evaluaciones.json` | Medición de evaluación | `tarea`, `metodo` |

## Idempotencia

Una entrada automática de inventario conserva `origen_tipo=recepcion` y
`origen_id` igual al identificador de recepción. El módulo de inventario
rechaza otra entrada para el mismo origen y SKU.

## Límites

JSON no proporciona una transacción multiarchivo. Por eso las validaciones se
ejecutan antes de escribir y QA revisa las relaciones posteriormente. Si el
volumen o la concurrencia aumentan, se deberá evaluar una migración respaldada
a SQLite, conservando los JSON originales y validando conteos.

Todos los archivos JSON usados por el código están listados en la tabla. Cada
entidad permanece en su propio archivo; no se combinan registros de compras con
otras entidades.
