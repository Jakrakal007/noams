# Reglas determinísticas

Las cinco reglas corresponden a implementaciones Python del registro de NOAMS. Producen indicadores de revisión, no prueban fraude ni incumplimiento definitivo. Las comparaciones se realizan sobre transacciones válidas. Los valores siguientes son los parámetros iniciales de la demo; las reglas configurables utilizan los valores persistidos en el catálogo.

## Duplicate Purchase — `DUPLICATE_PURCHASE`

**Objetivo:** identificar posibles compras repetidas dentro de una carga.

**Variables:** proveedor, orden de compra, monto y fila de origen. El proveedor se normaliza sin distinguir mayúsculas y colapsando espacios; la orden se recorta y compara sin distinguir mayúsculas.

**Criterio:** misma combinación proveedor/orden/monto. Se omiten órdenes vacías. La primera fila es la referencia y cada coincidencia posterior genera un hallazgo individual de categoría `duplicate`, con referencia a la transacción original.

**Severidad e impacto:** impacto igual al monto repetido. Baja por debajo de 500; media desde 500; alta desde 2.000; crítica desde 10.000. Confianza fija 0,95.

**Limitaciones:** no compara cargas diferentes, fechas o monedas; pagos legítimos repetidos pueden coincidir. No hay comparación aproximada de nombres.

## Unusual Supplier Amount — `UNUSUAL_SUPPLIER_AMOUNT`

**Objetivo:** detectar montos elevados frente al patrón histórico del proveedor.

**Variables:** monto actual, proveedor normalizado y montos de ejecuciones anteriores completadas. El servicio obtiene las últimas 10.000 transacciones históricas globales y después selecciona por proveedor. No incluye la carga actual.

**Criterio:** mínimo tres observaciones, mediana positiva, monto/mediana ≥ 3 y monto menos mediana ≥ 500. Parámetros: `minimum_history`, `multiplier`, `minimum_difference`.

**Hallazgo:** individual, categoría `unusual_amount`, con cantidad de observaciones, mediana, mínimo, máximo y razón. Impacto igual a la diferencia positiva frente a la mediana; desviación porcentual igual a diferencia/mediana × 100.

**Severidad:** media inicialmente; alta con razón ≥ 5 o diferencia ≥ 5.000; crítica con razón ≥ 10 o diferencia ≥ 20.000. Confianza = mínimo de 0,99 y `0,65 + min(n,10) × 0,02 + min(razón,10) × 0,01`.

**Limitaciones:** necesita cargas históricas previas; no segmenta por moneda, categoría, departamento o cantidad. El orden histórico es el de creación de análisis, no la fecha de compra. Los hallazgos previos también pueden formar parte del histórico.

## Budget Deviation — `BUDGET_DEVIATION`

**Objetivo:** identificar compras superiores al presupuesto informado.

**Variables:** `total_amount` y `budget_amount` de la fila.

**Criterio:** presupuesto presente y positivo, con monto estrictamente superior. Desviación = `(monto − presupuesto) / presupuesto × 100`.

**Hallazgo:** individual, categoría `budget_deviation`; impacto igual al exceso y evidencia de moneda. Confianza fija 1,0.

**Severidad:** baja por debajo del 10 %; media desde 10 %; alta desde 25 %; crítica desde 50 %. Parámetros: `medium_threshold_percentage`, `high_threshold_percentage`, `critical_threshold_percentage`.

**Limitaciones:** omite presupuestos ausentes o cero. El presupuesto es por registro; no agrega consumo por periodo ni verifica un presupuesto departamental externo.

## Purchase Without Valid Approval — `UNAPPROVED_PURCHASE`

**Objetivo:** priorizar operaciones con estados explícitos de aprobación de riesgo.

**Variables:** `approval_status` normalizado y monto. Los espacios del estado se sustituyen por guiones bajos.

**Criterio:** `pending`/`pendiente`, o `rejected`/`rechazado`/`unapproved`/`no_aprobado`. Otros estados no generan esta detección.

**Hallazgo:** individual, categoría `approval_risk`, con estado como evidencia e impacto igual al monto expuesto. Confianza fija 1,0.

**Severidad:** para el grupo pending, media debajo de 5.000 y alta desde 5.000. Para el grupo rejected, alta debajo de 10.000 y crítica desde 10.000. Parámetros: `approval_threshold` (5.000) y `critical_multiplier` (2).

**Limitaciones:** no consulta aprobaciones externas ni detecta cualquier texto desconocido como inválido. El estado proviene del archivo.

## Potential Split Purchase — `SPLIT_PURCHASE`

**Objetivo:** identificar grupos compatibles con un posible fraccionamiento.

**Variables:** proveedor, departamento y categoría normalizados; montos y fechas dentro de la misma carga.

**Criterio:** cada compra debe ser estrictamente inferior al umbral de 5.000. Por grupo se ordenan las compras por fecha e identificador. Se forma una ventana inclusiva de tres días desde cada primera operación no consumida; al menos dos compras deben sumar un monto ≥ 5.000. Los registros utilizados no se reutilizan en otro hallazgo de esta regla. Parámetros: `approval_threshold`, `window_days`, `minimum_operations`.

**Hallazgo:** agregado, categoría `split_purchase`, sin transacción individual vinculada. La evidencia conserva identificadores de todas las compras, fechas, montos, suma, umbral y ventana. Impacto igual a la suma del grupo; confianza fija 0,75.

**Severidad:** media inicialmente; alta desde dos veces el umbral; crítica desde cinco veces el umbral.

**Limitaciones:** la agrupación es voraz y no enumera todas las combinaciones posibles. No cruza cargas ni separa monedas. Un grupo de compras legítimas puede activar la regla.

## Interpretación común

La regla de precios unitarios fuera de rango no está implementada. El precio unitario sólo participa en validación numérica. No se entrenan modelos ni se utilizan servicios externos de detección.

La exposición es una aproximación por criterio de regla. El dashboard toma el máximo de los hallazgos abiertos vinculados a cada transacción y añade los hallazgos agregados; los agregados pueden solaparse con hallazgos individuales. El resumen de una ejecución suma todos sus hallazgos y puede contar la misma exposición más de una vez. No se convierten monedas: los ejemplos utilizan exclusivamente PEN.
