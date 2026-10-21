# Auditoría previa a la alineación

Fecha de revisión: 2026-08-27

Repositorio revisado: `sistema_profesional_compras_riesgo`

## Arquitectura encontrada

- Aplicación web monolítica pequeña en Python con Flask.
- `main.py` contiene la aplicación Flask y las rutas HTTP.
- `modules/` contiene persistencia, reglas de negocio, análisis, inventario y QA.
- `templates/` contiene las vistas HTML con Bootstrap y JavaScript mediante Fetch API.
- `data/` contiene archivos JSON. No se encontró una base de datos SQL.
- `tests/` utiliza `unittest` para pruebas unitarias y de endpoints.

## Estado de los datos observado

Los conteos se obtuvieron directamente de los archivos JSON del repositorio:

| Archivo | Registros observados |
|---|---:|
| `proveedores.json` | 3 |
| `compras.json` | 6 |
| `inventario.json` | 4 |
| `movimientos_inventario.json` | 0 |
| `procesos_compra.json` | 0 |
| `cotizaciones.json` | 0 |
| `negociaciones.json` | 0 |
| `seguimientos_compra.json` | 0 |
| `incidencias.json` | 0 |
| `recepciones.json` | 0 |
| `pagos.json` | 0 |
| `pagos_aplicados.json` | 0 |

Los archivos nuevos del expediente no contienen datos ficticios. Se inicializan
vacíos y sólo se llenan mediante las operaciones de la aplicación.

## Funcionalidades reutilizables

- Consulta de indicadores de vencimiento por proveedor.
- Gestión y validación de proveedores.
- Órdenes con partidas y cálculo de subtotal, impuestos y total.
- Consulta de inventario sin movimiento.
- Movimientos de entrada, salida y ajuste con actualización de existencia.
- QA de proveedores, compras, inventario y relaciones del expediente.
- Persistencia JSON centralizada en `modules/storage.py`.

## Diferencias detectadas respecto de la especificación

Antes de esta alineación faltaban o estaban incompletos:

- auditoría documentada del repositorio;
- módulo de evaluación antes/después para la tesis;
- estadísticas descriptivas de las mediciones;
- exportación CSV de métricas y evaluación;
- búsqueda global de proceso, orden, proveedor y producto;
- cierre con checklist y controles de integridad;
- historial consolidado por proveedor;
- filtros operativos para órdenes, inventario, incidencias y pagos;
- documentación separada de arquitectura, datos, flujo, métricas y pruebas.

## Riesgos técnicos

- JSON no ofrece transacciones multiarchivo. Las operaciones que escriben más de
  un archivo deben mantener idempotencia y validar antes de persistir.
- Los registros heredados tienen esquemas menos completos que los nuevos. Se
  deben normalizar al leer sin borrar ni inventar valores históricos.
- No existe autenticación. La herramienta se considera de uso local y no debe
  exponerse públicamente sin una capa de seguridad.
- Los resultados de eficiencia no pueden afirmarse hasta capturar mediciones
  reales con la plantilla de evaluación.

## Decisiones de alcance

- Se conserva Flask.
- Se conserva JSON por ahora; no se justifica una migración a SQL mientras el
  volumen siga siendo pequeño y el sistema mantenga validaciones e idempotencia.
- Los pagos se implementan como seguimiento operativo de obligaciones y saldos,
  no como contabilidad ni conciliación bancaria.
- No se incorpora machine learning, score arbitrario ni pronóstico.
- Los datos existentes no se sustituyen y los datos demo no se mezclan con ellos.

## Resultado de la auditoría

El MVP es reutilizable. La evolución correcta es consolidar el expediente de
compra y añadir evaluación, exportación, búsqueda, cierre y documentación, sin
reescribir la aplicación ni migrar automáticamente la persistencia.
