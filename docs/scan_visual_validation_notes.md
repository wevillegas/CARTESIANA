# Corrección del validador visual complementario

La primera ejecución auxiliar terminó a los 0,24 segundos simulados con
`AttributeError: 'NoneType' object has no attribute 'getSFVec3f'`. El test
consultaba `scale` suponiendo que el nodo visual siempre se exponía como
`Transform`. Webots puede representar un Transform unitario como `Pose`, cuya
definición local no tiene campo `scale`.

La evidencia previa se conserva en `scan_visual_initial_failure.json` y
`scan_visual_initial_failure_stderr.log`. La definición instalada
`resources/nodes/Pose.wrl` contiene traslación, rotación y children; la de
`Transform.wrl` añade escala, con valor por defecto `1 1 1`.

El auxiliar ahora consulta el tipo base real: acepta la escala implícita
unitaria exclusivamente para `Pose`, y exige un campo `scale` accesible para
`Transform`. Rechaza otros tipos. Además comprueba la matriz de pose relativa
al `X_MODULE` contra la identidad en el inicio y en las nueve posiciones.
La comparación global con el padre también se mantiene.

La causa fue una suposición del test auxiliar sobre la API; esta corrección
no modifica el PROTO, la física, los límites ni el controlador original.
La ejecución inicial se detuvo antes de los movimientos y no representa
una regresión cinemática medida. La validación completa se repitió con
el auxiliar corregido y aprobó las 34 comprobaciones; el informe final está
en `scan_visual_validation.json` y los logs finales no contienen errores ni warnings.
