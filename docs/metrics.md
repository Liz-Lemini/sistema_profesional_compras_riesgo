# Indicadores y evaluación

## Indicadores operativos

Los indicadores se calculan con registros existentes y una fecha de corte:

- monto y cantidad de compras vencidas;
- atraso promedio y máximo por proveedor;
- frecuencia de facturas vencidas por proveedor;
- monto total de compras;
- procesos abiertos por estado;
- incidencias abiertas;
- pagos vencidos con saldo positivo;
- pagos por vencer dentro de siete días, con saldo positivo;
- órdenes con fecha de entrega vencida que no estén recibidas ni canceladas;
- recepciones parciales, procesos estancados y proveedores incompletos;
- inventario bajo, inventario rezagado, capital inmovilizado y valor en exceso;
- calidad de datos aprobada por QA.

La atención de proveedores es binaria y operativa: `Requiere atención` si
existe al menos una compra vencida; de lo contrario, `Sin vencimientos`. No se
ponderan variables ni se calcula un score o una probabilidad.

## Evaluación antes/después

La pantalla `Evaluación` registra una observación real con tarea, método,
fecha, duración en segundos, errores y responsable. Para cada tarea y método
calcula `n`, media, mediana, mínimo, máximo y desviación estándar cuando hay al
menos dos observaciones.

Con ambas muestras disponibles:

```text
reducción de tiempo = (media manual - media sistema) / media manual × 100
```

Si no existe muestra o la media manual es cero, se muestra `N/D`. La aplicación
no genera mediciones ni afirma reducción de tiempos sin registros reales.
Las métricas descriptivas incluyen `n`, media, mediana, mínimo, máximo y
desviación estándar; esta última se informa únicamente con dos o más
observaciones. El archivo `data/evaluaciones.json` debe contener registros
capturados antes de que haya resultados comparativos.

## Exportaciones

- `/api/exportar/metricas.csv`: indicadores del periodo de corte y su `n`.
- `/api/exportar/evaluacion.csv`: comparación por tarea, método, muestra,
  medias, reducción y tasa de error.

Las exportaciones sirven como evidencia para el capítulo de evaluación, pero no
sustituyen el diseño de la muestra ni la observación del proceso.
