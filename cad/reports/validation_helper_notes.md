# Corrección del helper de validación CAD

La primera ejecución real de Webots aprobó las 34 comprobaciones del informe CAD y conservó sus reportes y logs. Después de finalizar Webots, el helper PowerShell falló al sumar los tamaños de archivos para generar `docs/cad_performance.json`.

La causa fue la exposición de la clave `bytes` de un `OrderedDictionary` ante `Measure-Object -Property bytes` en Windows PowerShell 5.1. Se corrigió únicamente el helper: cada registro de asset se convierte ahora en `[pscustomobject][ordered]@{...}`. No se modificaron controlador principal, configuración cinemática, CAD ni geometrías.

Verificación directa en Windows PowerShell 5.1.26100.9444: tres archivos, suma **1.141.125 bytes**, SHA256 de 64 caracteres hexadecimales válidos; parser sin errores. La comprobación coincide con la suma independiente de los tamaños del sistema de archivos. El wrapper completo se vuelve a ejecutar para producir la evidencia final de rendimiento.

La primera captura cercana tenía un encuadre insuficiente: `fieldOfView` es horizontal y el viewport utilizado tiene aproximadamente relación 2:1. Se aumentó la distancia de cámara con margen vertical (factor 2,6 y distancia mínima 0,7 m), manteniendo orientación FLU, centro calculado desde los vértices reales y restauración de la cámara. Esta corrección afecta solamente a la evidencia visual del controlador complementario.
