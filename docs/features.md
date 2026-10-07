# Funcionalidades

## Importación y calidad de datos

CSV en UTF-8 (con BOM opcional) y XLSX, primera hoja activa y valores almacenados de fórmulas. El límite inicial es 10 MiB. No se soporta XLS ni se recalculan fórmulas de Excel.

Columnas obligatorias: `transaction_id`, `transaction_date`, `supplier_name`, `department`, `category`, `quantity`, `unit_price`, `total_amount`, `approval_status`, `purchase_order`. Opcionales: `budget_amount`, `currency`. La columna de orden de compra es obligatoria, pero su valor puede estar vacío. Se rechazan columnas desconocidas, duplicadas o ausentes.

Se requieren identificador, proveedor, departamento, categoría y estado de aprobación no vacíos; fechas válidas; cantidad positiva; precios y montos finitos no negativos; presupuesto opcional no negativo. Las fechas admiten ISO y formatos día/mes/año o mes/día/año; ISO evita ambigüedad. Los decimales utilizan punto. No se comprueba que cantidad por precio coincida con el total ni se valida exhaustivamente el código de moneda o el catálogo de estados.

Cada fila inválida produce errores por campo y no genera transacciones ni hallazgos. Las filas válidas se normalizan y conservan con número de fila.

## Análisis y hallazgos

Cinco reglas ejecutan criterios documentados en [reglas](rules.md). Los resultados conservan severidad (`low`, `medium`, `high`, `critical`), impacto estimado, valores detectados/esperados cuando corresponden, evidencia y referencias de análisis/transacción. Los valores de confianza son heurísticos determinísticos, no probabilidades calibradas.

La API permite buscar hallazgos por categoría, severidad, regla, proveedor, fechas y análisis, con paginación. El estado inicial es `open`; no existe flujo de resolución ni una página independiente de hallazgos. La interfaz presenta hallazgos dentro de resultados y abre un diálogo de evidencia.

## Dashboard e historial

El dashboard muestra análisis guardados, registros procesados, hallazgos, riesgos críticos abiertos y exposición estimada. El contador de análisis incluye todas las ejecuciones guardadas, también fallidas. El historial agrupa por nombre exacto de archivo, muestra la versión más reciente y cantidad de versiones, y admite filtros de archivo/estado. El detalle de análisis conserva errores y resultados. La eliminación retira una ejecución y su archivo asociado.

El detalle JSON contiene transacciones; no hay tabla visual autónoma de transacciones. El resumen de cada análisis suma todos los impactos de sus hallazgos; el dashboard aplica una agregación distinta. Consultar las limitaciones en [validación](validation.md).

## Gestión de reglas

Catálogo de cinco reglas, activación/desactivación, parámetros validados, restablecimiento y estadísticas de ejecuciones, fallos y hallazgos. Las modificaciones afectan a nuevas cargas; no recalculan ejecuciones anteriores. Se conserva una instantánea de los parámetros aplicados en cada ejecución.

## Presentación y alcance

Interfaz EN/ES, temas claro/oscuro y preferencias locales en el navegador. OpenAPI permite explorar las rutas. No hay autenticación, permisos, exportación de informes, investigaciones ni integración con sistemas empresariales. La demo se ejecuta en la dirección de loopback con datos ficticios.
