# Validación y limitaciones

## Entorno y resultados

Verificación realizada el 6 de octubre de 2026 en Windows con Python 3.13.4. Las versiones directas probadas están fijadas en requirements.txt y requirements-dev.txt. Las dependencias transitivas se resuelven por pip; no se distribuye un lock completo.

- Instalación desde cero con los requirements finales en un segundo entorno virtual independiente: correcta.
- Comprobación de dependencias con pip check: sin incompatibilidades declaradas.
- Pruebas existentes más tres casos de demo (dos formatos y aislamiento): **66 pruebas aprobadas**. Repetidas en el entorno limpio: **66 aprobadas**.
- Aviso no bloqueante: Starlette señala la deprecación del uso de HTTPX en TestClient y sugiere HTTPX2. Las pruebas actuales funcionan con HTTPX.
- CSV y XLSX sintéticos: histórico de tres registros sin hallazgos, carga de ocho registros con exactamente un hallazgo de cada una de las cinco reglas, caso normal sin hallazgos y archivo de validación con una fila válida y una rechazada.
- Trazabilidad: transacciones, evidencia, configuración de ejecución, detalle JSON y páginas HTTP comprobados.
- Base nueva: cuatro migraciones aplicadas y dos análisis cargados por el pipeline. Repetir seed_database.py no añade registros.
- Arranque real mediante Uvicorn y solicitudes HTTP: dashboard, historial, detalle persistido, reglas, estado SQL, métricas, hallazgos, OpenAPI y JavaScript respondieron 200.
- Base inicial: 2 análisis, 11 registros, 5 hallazgos, 2 críticos e impacto estimado de 22.400 PEN.
- Aislamiento: la configuración rechaza bases ajenas a la copia y directorios de carga externos. La ejecución no necesita archivos privados.

## Cobertura

Las pruebas cubren validación de entradas, archivos vacíos/malformados, CSV/XLSX, persistencia, historial por versiones, consulta de hallazgos, eliminación, condiciones y severidad de reglas, configuración, activación/restablecimiento, omisión de reglas deshabilitadas y continuidad ante un fallo controlado de regla.

## Alcance no verificado

No se han ejecutado pruebas de carga, concurrencia, grandes volúmenes, recuperación ante interrupción, auditoría exhaustiva de vulnerabilidades de dependencias ni despliegue público. La instalación se comprobó en Windows/Python 3.13.4; otras plataformas y versiones compatibles de Python no se ejecutaron.

Las rutas HTML se verificaron por HTTP y las pantallas se identificaron inspeccionando plantillas y JavaScript. No se completó una prueba visual ni interacción end-to-end en navegador: la herramienta de navegador no pudo adjuntar su vista. Los cambios de idioma/tema y la apertura de diálogos no están verificados visualmente. No se distribuyen capturas de pantalla operativas.

## Limitaciones conocidas

- El sistema carece de autenticación y autorización. Las rutas de carga, cambio de reglas y eliminación son accesibles en la instancia local. El comando documentado escucha sólo en 127.0.0.1; un servicio público requeriría controles adicionales.
- El procesamiento es síncrono respecto al ciclo de la solicitud, sin cola ni workers. El límite por archivo no evita todos los escenarios de consumo excesivo, como XLSX altamente comprimidos.
- Los hallazgos señalan riesgos; no confirman fraude o pérdidas. La confianza es heurística.
- El histórico de montos atípicos depende de análisis previos completados y del máximo global de 10.000 transacciones recientes, no de una ventana de fechas de negocio.
- No se separan monedas al agrupar ni se convierten importes. La presentación utiliza S/; los archivos sintéticos están íntegramente en PEN.
- El impacto por análisis suma todos los hallazgos. El dashboard toma el máximo por transacción y añade agregados; puede existir solapamiento entre un agregado y los hallazgos individuales.
- No se validan todas las variantes de aprobación o moneda ni la igualdad cantidad × precio = total. La regla presupuestaria utiliza el presupuesto de cada fila, no un presupuesto acumulado.
- Los filtros de proveedor/fecha de hallazgos usan una unión a transacciones individuales y por ello no incluyen hallazgos agrupados de fraccionamiento.
- Una nueva carga del mismo archivo crea otra ejecución y altera el histórico; la agrupación visual por nombre no elimina ejecuciones previas.
- No hay pantalla autónoma de transacciones/hallazgos, flujo de resolución, módulo de investigaciones, informes, exportación ni gestión de proveedores.
- El botón de formatos del dashboard es informativo; no tiene un diálogo adicional implementado.
- Los downgrades de migraciones no revierten el esquema.

La demo está destinada a exploración local con información ficticia. Su alcance no equivale a una certificación de seguridad ni a validación de uso productivo.
