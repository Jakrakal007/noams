# Arquitectura

NOAMS utiliza un backend Python con FastAPI que sirve tanto la API JSON como las páginas Jinja2. El navegador carga HTML, CSS y JavaScript desde la misma aplicación. SQLite conserva los resultados mediante SQLAlchemy; Alembic administra cuatro revisiones del esquema.

```text
CSV UTF-8 / XLSX → POST de archivo
                  ↓
         Lectura y validación de columnas/filas
                  ↓
    Filas válidas → normalización → transacciones
                  ↓
  Histórico de ejecuciones anteriores + configuración
                  ↓
        Motor de cinco reglas determinísticas
                  ↓
    Hallazgos + evidencia + ejecuciones de reglas
                  ↓
       SQLAlchemy / SQLite / archivo local
                  ↓
    API JSON → dashboard y páginas Jinja2
```

## Componentes

| Directorio | Responsabilidad |
| --- | --- |
| `app/api/routes` | Contratos HTTP, dependencias y páginas. |
| `app/services/analysis.py` | Lectura CSV/XLSX, pipeline, histórico, métricas y eliminación. |
| `app/validators/analysis.py` | Validación de columnas, tipos y valores por fila. |
| `app/rules` | Contexto, registro, contrato, motor y cinco implementaciones. |
| `app/services/rules.py` | Catálogo, parámetros validados, activación y estadísticas. |
| `app/services/findings.py` | Consulta filtrable y paginada de hallazgos. |
| `app/database` | Modelos, sesiones, integridad referencial y migraciones. |
| `app/schemas` | Modelos Pydantic de entrada y salida. |
| `app/templates`, `app/static` | Páginas y comportamiento del navegador. |
| `demo` | Archivos sintéticos y carga inicial mediante el pipeline real. |

## Rutas

| Ruta | Uso |
| --- | --- |
| `GET /` | Dashboard y formulario de carga. |
| `GET /analysis` | Historial con filtro de archivo y estado. |
| `GET /analysis/{id}` | Resumen persistido, errores y hallazgos. |
| `GET /rules` | Catálogo y configuración de reglas. |
| `GET /api/health` | Estado de aplicación y conexión SQL. |
| `POST /api/analysis/upload` | CSV/XLSX multipart en el campo `file`. |
| `GET /api/analysis`, `GET /api/analysis/{id}` | Historial y detalle con transacciones. |
| `GET /api/analysis/metrics` | Métricas acumuladas. |
| `DELETE /api/analysis/{id}` | Elimina una ejecución, sus dependencias y archivo guardado. |
| `GET /api/findings`, `GET /api/findings/{id}` | Búsqueda y evidencia de hallazgos. |
| `GET /api/rules`, `GET /api/rules/{code}` | Catálogo y estadísticas. |
| `PATCH /api/rules/{code}` | Cambia activación o parámetros. |
| `POST /api/rules/{code}/reset` | Restablece la regla. |
| `GET /docs` | OpenAPI interactiva. |

## Persistencia y ejecución

Las tablas son `analysis_runs`, `transactions`, `analysis_validation_errors`, `findings`, `rule_executions` y `rule_configurations`, además del control de revisión de Alembic. Una ejecución conserva identificadores, archivo, recuentos, tiempos y estado. Las transacciones conservan la fila de origen. Los hallazgos incluyen evidencia JSON; cada ejecución de regla conserva versión, configuración aplicada, resultado y duración.

Las filas inválidas se registran y quedan fuera del motor. Los hallazgos y registros válidos se guardan en una transacción SQL; los fallos de una regla se registran sin detener las otras. El procesamiento ocurre durante la solicitud de carga: no hay cola ni workers de análisis.

El arranque crea `data/` y aplica migraciones. La configuración utiliza rutas derivadas del código de esta copia; base y cargas están restringidas a su directorio `data/`. Un `.env` opcional se lee sólo desde la raíz de la demo. No se necesita ese archivo para ejecutar el sistema.

El histórico usa hasta 10.000 transacciones más recientes de ejecuciones previas completadas según el identificador del análisis; no selecciona por fecha de negocio. El dashboard calcula el máximo impacto abierto por transacción y añade los hallazgos agrupados. Estos últimos pueden solaparse con exposiciones individuales; la cifra no representa una pérdida contabilizada.
