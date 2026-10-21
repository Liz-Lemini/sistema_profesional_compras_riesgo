# Pruebas

## Ejecución

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

## Cobertura funcional

- Validaciones y normalización de proveedores.
- Cálculo de partidas, impuestos y totales de órdenes.
- Indicadores de crédito y vencimiento.
- Entradas, salidas, ajustes y existencia negativa.
- Ajustes con dirección obligatoria e idempotencia por origen y SKU.
- Creación de expediente, cotización, comparación y selección justificada.
- Negociación, generación de orden y rechazo de orden duplicada.
- Recepción y movimiento automático de inventario.
- Obligación, saldo y aplicación parcial de pago.
- Mediciones, tamaños de muestra y reducción de tiempo.
- API, vistas principales, búsqueda y exportación.
- Fechas de corte válidas e inválidas, respuesta JSON de errores de
  persistencia y renderizado de las nueve vistas.
- QA de registros, relaciones, totales y saldos.
- Ciclo HTTP completo con selección, negociación, orden, incidencia resuelta,
  recepción, pagos parciales/totales y cierre en un directorio temporal.

Las pruebas usan datos controlados o mocks; la prueba de ciclo por API crea
sus registros dentro de `TemporaryDirectory` y no altera los JSON del proyecto.
Estos casos no representan resultados operativos de la empresa.

La suite completa debe ejecutarse antes de entregar. Los casos de fechas que
dependen del día de ejecución deben usar fechas relativas o una fecha de
referencia controlada para evitar fallas por fixtures vencidos.

Última verificación: 6 de octubre de 2026, 37 pruebas aprobadas con el comando
indicado arriba. El ciclo por API usa datos temporales y no representa
mediciones de la operación real.
