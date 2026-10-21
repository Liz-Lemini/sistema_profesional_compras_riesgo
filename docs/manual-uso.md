# Manual de uso del sistema

Este manual describe la interfaz que existe en las plantillas del proyecto. La
aplicación es local y guarda información en archivos JSON dentro de `data/`.
Antes de una operación real, conserva una copia de respaldo de esa carpeta.

## Inicio

Desde la carpeta del proyecto, inicia el servidor:

```bash
./.venv/bin/python main.py
```

Abre `http://127.0.0.1:5001`. Para cerrar el servidor, usa `Ctrl+C` en la
terminal donde se inició.

La barra de navegación lleva a Resumen, Compras, Proveedores, Inventario,
Procesos, Evaluación y Búsqueda.

## Resumen

La pantalla inicial presenta proveedores y compras registrados, monto total,
monto vencido, expedientes abiertos y alertas. La tarjeta destacada identifica
al proveedor con el mayor monto vencido. La tabla permite revisar vencimientos,
atraso promedio y máximo, y el control de calidad muestra sus validaciones.
Las alertas de expedientes incluyen un enlace al expediente cuando existe una
relación directa.

La etiqueta del proveedor significa `Requiere atención` si tiene una o más
compras vencidas; de lo contrario, `Sin vencimientos`. No es un score ni una
predicción.

## Proveedores

En Proveedores, registra nombre, asesor, teléfono, días de crédito y, cuando
aplique, correo, sector y notas. El teléfono debe tener entre 10 y 15 dígitos;
los días de crédito no pueden ser negativos. La tabla permite buscar y filtrar
por estado, editar datos, activar o desactivar el proveedor y abrir su historial.

El detalle del proveedor reúne cotizaciones, órdenes, incidencias y pagos
asociados. Completa los campos obligatorios antes de activar un registro
heredado incompleto.

## Compras

Compras permite registrar una orden con proveedor, factura, fecha, crédito,
entrega, estado, impuestos, observaciones y una o más partidas. El sistema
calcula subtotal y total. Puedes buscar, filtrar y cambiar el estado desde la
tabla; el crédito aparece como vigente o vencido según la fecha de corte.

Las órdenes generadas desde un expediente reutilizan la cotización y la
negociación seleccionadas y quedan vinculadas a ese expediente.

## Procesos de compra

En Procesos, crea una necesidad con producto o descripción, cantidad,
prioridad, motivo, fecha, responsable y observaciones. Busca expedientes por
texto o filtra por estado, prioridad, proveedor y fechas.

Abre un folio para trabajar el ciclo completo:

1. Registra las cotizaciones de proveedores activos, incluyendo precio,
   envío, impuestos, crédito, plazo, fecha y disponibilidad.
2. Compara los costos totales y consulta los destacados de menor costo, mayor
   crédito y menor plazo. Son referencias; la decisión queda a cargo del
   usuario.
3. Selecciona una cotización y escribe la justificación obligatoria.
4. Registra la negociación y genera la orden de compra.
5. Añade eventos de seguimiento, incidencias y recepciones. Las unidades
   aceptadas se reflejan como entradas de inventario con referencia a la
   recepción. Las incidencias registradas aparecen debajo del formulario;
   actualiza su estado y escribe la resolución o justificación para completar
   el checklist.
6. Registra la obligación de pago y, cuando corresponda, aplica pagos
   parciales o totales para actualizar el saldo. Para cerrar, el checklist
   requiere que la obligación esté registrada o que el pago se marque como no
   aplicable.
7. Revisa el checklist de cierre. El sistema solo permite completar el
   expediente cuando todas las validaciones aplicables están resueltas.

El historial conserva los eventos asociados al expediente y la sección de
negociaciones muestra sus registros.

## Inventario

Inventario muestra existencias actuales y mínimas, artículos rezagados,
capital inmovilizado, valor en exceso y movimientos recientes. Para registrar
una entrada o salida, selecciona SKU, tipo, cantidad, fecha y observaciones.
En un ajuste también indica si incrementa o decrementa. Una salida no puede
superar la existencia disponible. El inventario rezagado considera 90 días o
más sin movimiento.

Las entradas creadas desde una recepción se registran automáticamente y no se
deben volver a capturar manualmente.

## Evaluación antes/después

Registra cada observación real con tarea, método (`manual` o `sistema`), fecha,
duración, errores, responsable y notas. Usa el mismo criterio para ambas
muestras. Mientras falte una muestra o la media manual sea cero, la reducción
aparece como `N/D`. El sistema no crea mediciones automáticamente.

Los botones de exportación descargan los indicadores operativos y el resumen
de evaluación como CSV UTF-8 con BOM.

## Búsqueda

Busca con al menos dos caracteres. La respuesta se divide en procesos,
proveedores, órdenes e inventario; puedes abrir cada sección para continuar en
su pantalla correspondiente.

## Alcance y cuidado de datos

No hay autenticación. Ejecuta el sistema en el entorno local previsto y no lo
expongas directamente a Internet. Los JSON no ofrecen transacciones entre
archivos; conserva respaldos de `data/` y revisa QA si una operación se
interrumpe. Los pagos son un registro operativo, no un sistema contable. No se
capturaron mediciones comparativas en el conjunto de datos entregado, por lo
que el sistema no debe presentarse como evidencia de porcentajes de mejora.
