# Arquitectura real

## Capas

```text
Flask / main.py
        ↓
Módulos de negocio
gestion.py · proceso.py · inventario.py · evaluacion.py · analisis.py · qa.py
        ↓
Persistencia JSON
storage.py → data/*.json
```

La aplicación es un monolito web local. Flask se utiliza para declarar rutas
HTTP, renderizar plantillas Jinja y ofrecer la API JSON con una dependencia
externa mínima; no se agrega otro framework. Las rutas reciben las solicitudes,
los módulos aplican las reglas de negocio y `storage.py` concentra la lectura y
escritura de archivos JSON.

## Decisiones

- Se conserva Flask, sin frontend adicional.
- Los datos se mantienen en JSON porque el volumen actual es pequeño y la
  aplicación ya utiliza esta persistencia. No se afirma que sea una base de
  datos SQL.
- La integridad referencial se valida en los módulos y en QA.
- Las operaciones que pueden repetirse, como la entrada de inventario por una
  recepción, usan una referencia de origen para evitar duplicados.
- No se incorporan modelos predictivos ni un score arbitrario de proveedores.
- No se incorpora autenticación; el alcance previsto es una herramienta local
  de apoyo al área, no un servicio público multiusuario.
- Las exportaciones CSV se construyen con la biblioteca estándar y llevan BOM
  UTF-8 para facilitar su apertura en hojas de cálculo.

## Componentes

| Componente | Responsabilidad |
|---|---|
| `main.py` | Vistas y API HTTP |
| `gestion.py` | Proveedores y órdenes heredadas/nuevas |
| `proceso.py` | Expediente integrado y reglas de ciclo de compra |
| `inventario.py` | Existencias y movimientos |
| `analisis.py` | Indicadores de compras y alertas operativas |
| `evaluacion.py` | Mediciones y estadística descriptiva |
| `qa.py` | Validación de calidad e integridad |
| `storage.py` | Persistencia segura en JSON |

## Límites operativos

La persistencia en archivos JSON no proporciona transacciones entre entidades
ni control de concurrencia. Las validaciones se ejecutan antes de escribir; las
operaciones que relacionan más de un archivo pueden requerir reconciliación
por QA si el proceso se interrumpe a mitad de una escritura. No se almacenan
mediciones antes/después mientras no se registren observaciones reales.
