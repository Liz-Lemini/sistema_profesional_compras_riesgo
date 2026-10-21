# Sistema Profesional de Compras y Logística Empresarial

Aplicación web desarrollada en Python con Flask para organizar el proceso de
compras y logística mediante expedientes trazables: necesidad, cotizaciones,
comparación, negociación, orden, seguimiento, recepción, inventario y pagos.
El sistema conserva el MVP y agrega el flujo integrado para operaciones nuevas.

## Inicio rápido

### Windows (PowerShell)

Abre **PowerShell** en la carpeta del proyecto. Si está en el Escritorio, puedes
entrar con:

```powershell
cd "$HOME\Desktop\sistema_profesional_compras_riesgo"
```

Comprueba que Python esté instalado (`py --version`) y ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Después abre [http://127.0.0.1:5001](http://127.0.0.1:5001) en el navegador.
Deja abierta PowerShell mientras uses la aplicación. Para detener el servidor,
presiona `Ctrl+C`.

La creación del entorno virtual y la instalación se hacen una sola vez. En los
siguientes usos, abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
.\.venv\Scripts\python.exe main.py
```

Si el comando `py` no está disponible, instala Python 3 y habilita el Python
Launcher durante la instalación, o usa `python` en lugar de `py` para crear el
entorno virtual.

Para elegir otro puerto, por ejemplo `5000`:

```powershell
$env:PORT = "5000"
.\.venv\Scripts\python.exe main.py
```

Abre `http://127.0.0.1:5000`. Para volver al puerto predeterminado en esa
ventana de PowerShell, ejecuta `Remove-Item Env:PORT`.

### macOS

Abre **Terminal** y ejecuta estos comandos desde la carpeta del proyecto:

```bash
cd ~/Desktop/sistema_profesional_compras_riesgo
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python main.py
```

Después abre [http://127.0.0.1:5001](http://127.0.0.1:5001) en el navegador.
Deja abierta la ventana de Terminal mientras uses la aplicación. Para detener el
servidor, vuelve a esa ventana y presiona `Ctrl+C`.

La creación del entorno virtual y la instalación se hacen una sola vez. En los
siguientes usos basta con:

```bash
cd ~/Desktop/sistema_profesional_compras_riesgo
./.venv/bin/python main.py
```

Se usa el puerto `5001` por defecto. Para elegir otro puerto, por ejemplo `5000`:

```bash
PORT=5000 ./.venv/bin/python main.py
```

En ese caso, abre `http://127.0.0.1:5000`.

## Tecnologías

- Python 3.x
- Flask
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Fetch API
- JSON como capa de persistencia

## Funciones del sistema

- Resumen operativo de compras y vencimientos por proveedor.
- Indicadores de atraso, frecuencia de vencimiento y monto vencido.
- Registro de nuevas compras desde interfaz web.
- Gestión de órdenes con partidas, cantidades, precios, impuestos y total calculado.
- Seguimiento de estados de orden y fecha de entrega.
- Visualización del estado de créditos `Vigente` y `Vencida`.
- Registro, edición, búsqueda y activación/desactivación de proveedores.
- Validación de teléfono, correo, días de crédito y duplicados.
- Módulo de inventario sin movimiento.
- Identificación de stock sin movimiento por 90 días o más.
- Cálculo de capital inmovilizado y valor en exceso.
- Consulta de existencias y alerta de existencia baja frente al mínimo.
- Registro de entradas y salidas con fecha, SKU, cantidad y observaciones.
- Ajustes de inventario con dirección explícita y origen trazable.
- Reconciliación de existencias contra movimientos cuando existe una línea base.
- Expedientes de compra con folio `PC-AAAA-NNNN`.
- Cotizaciones comparables con costo total, crédito, plazo y disponibilidad.
- Selección de proveedor con justificación obligatoria.
- Negociación registrada y orden generada desde la cotización seleccionada.
- Seguimiento, incidencias, recepciones parciales/completas y entrada automática al inventario.
- Obligaciones de pago y aplicaciones parciales o completas con saldo calculado.
- QA de proveedores, compras, inventario y expediente integrado.
- Búsqueda global agrupada por procesos, proveedores, órdenes e inventario.
- Exportaciones CSV de indicadores y evaluación con BOM UTF-8.
- Navegación web unificada con diseño uniforme.

## Indicadores de seguimiento

El sistema no presenta un score predictivo de proveedores. Utiliza indicadores
operativos calculables con los registros disponibles:

- atraso promedio de compras vencidas;
- máximo atraso observado;
- frecuencia de facturas vencidas;
- monto vencido;
- monto total de compras.

La regla de atención es explícita:

- `Sin vencimientos`: no existen compras vencidas para el proveedor;
- `Requiere atención`: existe al menos una compra vencida.

Los indicadores se calculan respecto a una fecha de corte:

```text
Días restantes = Días de crédito - (Fecha de corte - Fecha de compra)
```

## Estructura del proyecto

```text
sistema_profesional_compras_riesgo/
├── data/
│   ├── compras.json
│   ├── cotizaciones.json
│   ├── evaluaciones.json
│   ├── incidencias.json
│   ├── inventario.json
│   ├── movimientos_inventario.json
│   ├── negociaciones.json
│   ├── pagos.json
│   ├── pagos_aplicados.json
│   ├── procesos_compra.json
│   ├── proveedores.json
│   ├── recepciones.json
│   └── seguimientos_compra.json
├── docs/
│   ├── architecture.md
│   ├── audit-before-refactor.md
│   ├── audit-tesis-vs-codigo.md
│   ├── data-model.md
│   ├── implementation-report.md
│   ├── manual-uso.md
│   ├── matriz_trazabilidad.md
│   ├── metrics.md
│   ├── plantilla_medicion.md
│   ├── testing.md
│   ├── thesis-traceability.md
│   └── workflow.md
├── modules/
│   ├── __init__.py
│   ├── analisis.py
│   ├── evaluacion.py
│   ├── gestion.py
│   ├── inventario.py
│   ├── proceso.py
│   ├── qa.py
│   └── storage.py
├── templates/
│   ├── base.html
│   ├── buscar.html
│   ├── compras.html
│   ├── evaluacion.html
│   ├── index.html
│   ├── inventario.html
│   ├── proceso_detalle.html
│   ├── procesos.html
│   ├── proveedor_detalle.html
│   └── proveedores.html
├── tests/
│   ├── test_analisis.py
│   ├── test_api.py
│   ├── test_compras.py
│   ├── test_end_to_end.py
│   ├── test_evaluacion.py
│   ├── test_gestion.py
│   ├── test_inventario.py
│   ├── test_proceso.py
│   └── test_qa.py
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

### Qué ocurre cuando se usa la aplicación

1. El navegador solicita una vista como `/procesos` o `/inventario`.
2. `main.py` atiende la ruta y renderiza la plantilla HTML correspondiente en
   `templates/`.
3. La página consulta o envía datos a las rutas `/api/...` mediante JavaScript y
   Fetch API.
4. La ruta API valida la solicitud y llama a la función del módulo de negocio
   correspondiente dentro de `modules/`.
5. Los módulos leen o guardan los registros en archivos JSON dentro de `data/`;
   la respuesta vuelve al navegador como JSON y la interfaz se actualiza.

En resumen, las responsabilidades están separadas así:

| Carpeta/archivo | Responsabilidad |
|---|---|
| `main.py` | Arranque de Flask, vistas web, API, validación de parámetros y respuestas HTTP. |
| `modules/` | Reglas de negocio, análisis de indicadores, inventario, evaluación, QA y persistencia. |
| `templates/` | Pantallas HTML y código de interfaz que consume la API. |
| `data/` | Registros operativos persistidos como archivos JSON. |
| `tests/` | Pruebas automatizadas de módulos, API y flujo integrado. |
| `docs/` | Manual, arquitectura, modelo de datos, trazabilidad y documentación del proyecto. |
| `requirements.txt` | Dependencias Python que se instalan en el entorno virtual. |

`modules/storage.py` es la capa común de acceso a JSON. Los demás módulos
concentran las reglas de cada área; por ejemplo, `modules/proceso.py` gestiona
expedientes, cotizaciones, recepciones e incidencias, mientras
`modules/inventario.py` gestiona existencias y movimientos.

## Módulos principales

### `main.py`

- Inicializa el servidor Flask.
- Define las rutas web y endpoints JSON.

### `modules/storage.py`

- Lee y escribe archivos JSON.
- Crea carpetas automáticamente si no existen.
- Maneja errores de persistencia.

### `modules/analisis.py`

- Calcula indicadores operativos de vencimiento por proveedor.
- Construye el resumen general.
- Resume procesos abiertos, incidencias y pagos vencidos.
- Ordena proveedores por monto vencido y atraso.

### `modules/gestion.py`

- Lista, registra, edita y cambia el estado de proveedores.
- Lista y registra órdenes de compra con partidas y totales consistentes.
- Actualiza el estado de las órdenes.
- Calcula el estado actual del crédito por compra.

### `modules/inventario.py`

- Consulta existencias y analiza inventario sin movimiento.
- Detecta materiales con más de 90 días sin movimiento.
- Calcula capital inmovilizado y valor en exceso.
- Registra entradas, salidas y ajustes sin permitir existencias negativas.
- Conserva un historial separado en `data/movimientos_inventario.json`.

### `modules/proceso.py`

- Mantiene expedientes con folio, estado, prioridad y eventos.
- Relaciona cotizaciones, selección, negociación y órdenes de compra.
- Registra seguimiento, incidencias y recepciones.
- Genera movimientos de entrada desde recepciones aceptadas.
- Calcula obligaciones, aplicaciones y saldos de pago.

### `modules/qa.py`

- Ejecuta validaciones de integridad sobre proveedores, compras, inventario y expedientes.
- Detecta duplicados, fechas inválidas o futuras, montos incorrectos y compras sin proveedor.
- Revisa relaciones entre procesos, cotizaciones, órdenes, recepciones e incidencias.
- Revisa totales de cotizaciones y saldos de pagos.
- Identifica referencias de los registros afectados para facilitar su corrección.
- Expone el resultado mediante `run_quality_assurance()` y `/api/qa`.

### `modules/evaluacion.py`

- Registra mediciones reales del método manual o del sistema.
- Calcula tamaño de muestra, media, mediana, mínimo, máximo y desviación estándar.
- Calcula reducción de tiempo sólo cuando existen ambas muestras.

## Rutas disponibles

### Vistas HTML

- `/` Resumen principal
- `/compras` Gestión de compras
- `/proveedores` Gestión de proveedores
- `/inventario` Inventario sin movimiento
- `/procesos` Expedientes integrados de compra
- `/procesos/<id>` Detalle de un expediente y sus etapas
- `/proveedores/<id>` Historial integrado del proveedor
- `/evaluacion` Evaluación antes/después
- `/buscar?q=...` Búsqueda global

### API JSON

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/dashboard` | Indicadores y alertas operativas |
| GET, POST | `/api/proveedores` | Listar y registrar proveedores |
| PUT | `/api/proveedores/<id>` | Editar proveedor |
| PATCH | `/api/proveedores/<id>/estado` | Activar o desactivar proveedor |
| GET | `/api/proveedores/<id>/historial` | Historial integrado del proveedor |
| GET, POST | `/api/compras` | Listar y registrar órdenes |
| PUT | `/api/compras/<id>` | Editar orden |
| PATCH | `/api/compras/<id>/estado` | Actualizar estado de orden |
| GET | `/api/inventario` | Indicadores y existencias |
| GET, POST | `/api/inventario/movimientos` | Consultar y registrar movimientos |
| GET | `/api/qa` | Validaciones de calidad de datos |
| GET, POST | `/api/procesos` | Listar y crear expedientes |
| GET, PUT | `/api/procesos/<id>` | Consultar y editar expediente |
| PATCH | `/api/procesos/<id>/estado` | Cambiar estado del expediente |
| GET | `/api/procesos/<id>/cierre` | Consultar checklist de cierre |
| POST | `/api/procesos/<id>/cerrar` | Cerrar expediente validado |
| GET, POST | `/api/procesos/<id>/cotizaciones` | Comparar y agregar cotizaciones |
| POST | `/api/procesos/<id>/cotizaciones/<cotizacion_id>/seleccionar` | Seleccionar cotización con justificación |
| POST | `/api/procesos/<id>/negociaciones` | Registrar negociación |
| POST | `/api/procesos/<id>/orden` | Generar orden desde expediente |
| POST | `/api/procesos/<id>/seguimiento` | Registrar seguimiento |
| POST | `/api/procesos/<id>/incidencias` | Registrar incidencia |
| POST | `/api/procesos/<id>/recepciones` | Registrar recepción |
| POST | `/api/procesos/<id>/pagos` | Registrar obligación de pago |
| POST | `/api/pagos/<id>/aplicar` | Aplicar pago al saldo |
| PATCH | `/api/incidencias/<id>/estado` | Actualizar estado y resolución de incidencia |
| GET, POST | `/api/evaluacion` | Consultar y guardar mediciones |
| GET | `/api/busqueda?q=...` | Buscar en procesos, proveedores, órdenes e inventario |
| GET | `/api/exportar/metricas.csv` | Exportar indicadores |
| GET | `/api/exportar/evaluacion.csv` | Exportar comparación de mediciones |

Los endpoints de indicadores aceptan opcionalmente `fecha_corte=AAAA-MM-DD`
(`/api/dashboard`, `/api/compras`, `/api/inventario` y `/api/qa`) para repetir
una consulta con una fecha de referencia explícita.

## Cómo ejecutar el proyecto

Las instrucciones rápidas para Windows y macOS están al inicio de este README.
Como referencia, en macOS desde Terminal, entra a la carpeta del proyecto:

```bash
cd ~/Desktop/sistema_profesional_compras_riesgo
```

Crear el entorno e instalar dependencias:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Iniciar servidor:

```bash
./.venv/bin/python main.py
```

Abrir en navegador:

```text
http://127.0.0.1:5001
```

La aplicación usa el puerto 5001 por defecto porque macOS puede reservar el
puerto 5000 para AirPlay Receiver. Si se necesita usar el puerto 5000 y está
libre, iniciar así:

```bash
PORT=5000 ./.venv/bin/python main.py
```

En ese caso, abrir `http://127.0.0.1:5000`.

Ejecutar pruebas:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

## Persistencia de datos

El sistema no utiliza base de datos relacional. Toda la información se guarda en archivos JSON dentro de la carpeta `data/`.

Archivos usados:

- `data/compras.json`
- `data/proveedores.json`
- `data/inventario.json`
- `data/movimientos_inventario.json` (se crea al registrar o revisar movimientos)
- `data/procesos_compra.json`
- `data/cotizaciones.json`
- `data/negociaciones.json`
- `data/seguimientos_compra.json`
- `data/incidencias.json`
- `data/recepciones.json`
- `data/pagos.json`
- `data/pagos_aplicados.json`
- `data/evaluaciones.json`

## Estado actual del proyecto

El sistema actualmente permite:

- Consultar el resumen de compras y vencimientos.
- Registrar, editar, buscar y activar/desactivar proveedores.
- Registrar órdenes con partidas y total calculado.
- Consultar y actualizar el estado de las órdenes.
- Crear expedientes, comparar cotizaciones y justificar la selección.
- Generar órdenes desde un expediente seleccionado.
- Registrar recepciones y actualizar existencias aceptadas.
- Registrar obligaciones y aplicaciones de pago con saldo.
- Revisar créditos por vencer o vencidos.
- Consultar inventario sin movimiento.
- Consultar existencias y registrar entradas, salidas y ajustes trazables.
- Consultar alertas por procesos prioritarios/estancados, incidencias, pagos, retrasos, recepciones y existencias bajas.
- Buscar globalmente procesos, proveedores, órdenes e inventario.
- Revisar la calidad de los datos operativos.
- Registrar mediciones reales y exportar evidencia para evaluación.

La relación entre objetivos, funcionalidades, pruebas, evidencias y métricas
se documenta en `docs/matriz_trazabilidad.md`. Las métricas del proceso
anterior y posterior deben levantarse con datos reales; no se incluyen valores
inventados. La captura puede organizarse con `docs/plantilla_medicion.md`.

## Alcance y límites

Los pagos implementados son un registro operativo de obligaciones y
aplicaciones; no sustituyen una conciliación bancaria ni un sistema contable.
La aplicación no incluye autenticación, score de proveedores, modelos
predictivos ni pronósticos. No hay mediciones antes/después capturadas en el
repositorio; por ello no se reportan porcentajes de mejora. Los indicadores se
calculan únicamente con los registros disponibles. La persistencia JSON no
ofrece transacciones multiarchivo y los pagos no sustituyen un sistema contable.
