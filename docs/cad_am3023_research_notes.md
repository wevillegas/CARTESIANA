# Beckhoff AM3023: investigación de fabricante

Consulta: 2026-09-29 en Argentina / 2026-09-30 UTC. Se descargaron únicamente dos variantes AM3023 oficiales y el manual técnico relevante. No se modificaron las referencias fotográficas ni los archivos originales de CAD descargados.

## Fuentes

- [Repositorio STEP oficial AM30xx](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AM30xx): publica `am3023-1xx0_stp.zip` y `am3023-1xx1_stp.zip`.
- [Producto oficial AM3023-wCyz-000a](https://www.beckhoff.com/en-en/support/service-products/motion-service-products/am3023-wcyz-000a.html): nomenclatura vigente y dimensiones de la familia.
- [Manual AM3000 / AM3500, versión 1.5](https://download.beckhoff.com/download/Document/motion/am3000_am3500_ba_en.pdf): clave de pedido, página 14; dibujo AM302x, página 41.
- [Términos de uso de Beckhoff](https://www.beckhoff.com/en-en/terms-of-use/): procedencia y condiciones generales. No se encontró licencia abierta específica dentro de los ZIP. El manual conserva copyright de Beckhoff; no se conceden derechos de redistribución en este proyecto. Uso previsto: consulta y representación local académica, sin publicación externa de assets.

## Nomenclatura y correspondencia

En `AM30uv-wxyz-000a`, `u=2` identifica flange 58 mm y `v=3` la longitud de motor; `w=0` es eje liso y `w=1` incluye chavetero. `x=C` identifica bobinado; `y=4` es feedback BiSS multiturn; `z=0/1` indica ausencia/presencia de freno. `a=0` selecciona conectores angulares giratorios. Estos significados están confirmados por el fabricante.

| Pieza fotografiada | CAD publicado | Diferencia conocida | Clase propuesta |
| --- | --- | --- | --- |
| AM3023-0C40-0000 | AM3023-1xx0 | Chavetero del CAD; bobinado y feedback quedan genéricos en el nombre | B: carcasa de familia, geometría STEP verificada |
| AM3023-0C41-0000 | AM3023-1xx1 | Chavetero del CAD; bobinado y feedback quedan genéricos en el nombre | B: carcasa de familia con freno, geometría STEP verificada |

Ninguno es clase A: no hay prueba de un STEP del part number completo observado. No se debe rebautizar el CAD como `0C40` o `0C41` exacto. La geometría del eje del CAD sigue mostrando el chavetero, salvo una derivación expresamente documentada. La selección de variante de freno debe conservarse aunque el eje esté oculto dentro del montaje.

## Dibujo y medidas de control

El dibujo oficial muestra flange cuadrado de 58 mm, centrador Ø40 j6, eje Ø9 k6 con longitud libre de 20 mm, cuatro agujeros Ø4,8 en círculo Ø63 y dos conectores separados 28 mm. Los conectores sobresalen 39 mm sobre el cuerpo de 58 mm: el envelope completo con conectores tiene aproximadamente 97 mm en esa dirección. Las mediciones manuales `60×60` corresponden razonablemente a la sección de carcasa, pero no son un control del envelope completo de conectores.

Las cotas `Y=133,4` y `Z=167,5` parten del plano frontal de flange y terminan en la trasera de carcasa, sin incluir los 20 mm de eje libre. Por tanto, la longitud axial completa esperada es 153,4 mm sin freno y 187,5 mm con freno. La letra Z del dibujo es una cota del fabricante; no es el eje Z del robot.

| Control | CAD/dibujo (mm) | Medida manual (mm) | CAD menos real (mm) | Diferencia absoluta % | Lectura |
| --- | ---: | ---: | ---: | ---: | --- |
| Ancho flange | 58 | 60 | -2 | 3,33 | Compatible con medición aproximada |
| Alto carcasa | 58 | 60 | -2 | 3,33 | Compatible; excluye conectores |
| Longitud carcasa sin freno | 133,4 | 200 X/Y | -66,6 | 33,30 | Extremos manuales no documentados |
| Longitud con eje sin freno | 153,4 | 200 X/Y | -46,6 | 23,30 | Discordancia grande a registrar |
| Longitud carcasa con freno | 167,5 | 240 Z | -72,5 | 30,21 | Extremos manuales no documentados |
| Longitud con eje con freno | 187,5 | 240 Z | -52,5 | 21,88 | Discordancia grande a registrar |

No se atribuye automáticamente el excedente a un acople, reductor o soporte: falta una medición que lo demuestre. Tampoco se escala el motor a 200/240 mm. La información oficial y las placas identifican la familia, pero las longitudes aproximadas de campo no verifican sus extremos. Antes de usar el modelo para layout mecánico, medir flange a trasera de motor y flange a punta de eje por separado.

## Evidencia fotográfica

- `docs/reference_previews/IMG_0275.jpg`: placa legible `AM3023-0C41-0000`, freno `Br. 24 VDC`, identificación de máquina `+EXT -13M1`, orientación vertical. La relación con Z se infiere de la vista completa de la máquina y la orientación; no procede de la nomenclatura Beckhoff.
- `docs/reference_previews/IMG_0280.jpg`: placa legible `AM3023-0C40-0000`, identificación `+EXT -9M1`, orientación horizontal. Esta toma sola no determina de manera inequívoca si corresponde a X o Y.
- `docs/reference_previews/IMG_0283.jpg`: logo y normas, sin número de modelo legible; no sirve para discriminar variante.

Las fotos muestran la carcasa negra rectangular, extremos de flange y conectores angulares de la familia. No permiten medir el shaft oculto ni los agujeros con precisión.

## Archivos preservados

| Archivo en `cad/source/beckhoff` | Formato | Bytes | SHA256 |
| --- | --- | ---: | --- |
| am3023-1xx0_stp.zip | ZIP | 446884 | `4FA845F53C9FE9237F3B6F1BF993FC7953542D94BD74C423898A5A401BD87749` |
| AM3023-1xx0.step | STEP AP214 | 2477003 | `D35F2877596C5495A2905BE1C80671CCA097CEA173DB05A0AC7D88BBEDA2CD35` |
| am3023-1xx1_stp.zip | ZIP | 453078 | `F9D1998738C678429F493EBAE884A4358AAFC864E5F287CE3D2943AF03844669` |
| AM3023-1xx1.step | STEP AP214 | 2583682 | `C1B03DBFBDC256F13E44F4D73003205D634F8BBB695BAE4CF5645AF41CAD281E` |
| am3000_am3500_ba_en.pdf | PDF | 3578630 | `EAB989658D9D810374F07DA8292285BC43F7E437D0B4500B5750E746D7A92BF6` |

Los STEP provienen de SolidWorks 2008, con fechas internas 2008-07-11. Declaran unidades milímetros mediante `SI_UNIT(.MILLI., .METRE.)`. La conversión a Webots debe usar factor uniforme 0,001 para pasar a metros. Las imágenes de `cad/reports/am302x_manual_*` son evidencia local extraída/renderizada del PDF, no CAD adicional.

## Criterio de integración

Los reportes `cad/reports/am3023_no_brake_conversion.json` y `am3023_brake_conversion.json` confirman con OpenCascade los envelopes nativos `58×97×153,4 mm` y `58×97×187,5 mm`. Ambos reproducen las cotas de fabricante. Cada STEP contiene un BRep sólido válido y 615 caras.

La inspección adicional `tools/inspect_am3023_mounting.py` genera `cad/reports/am3023_mounting_features.json` sin escribir sobre el STEP. Confirma pilot Ø40, eje Ø9 y los cuatro agujeros Ø4,8, cuyos centros están en `X/Y=±22,273864 mm` (círculo Ø63). El plano de montaje nativo está en `Z=-0,8 mm`; la punta del eje está en `Z=19,2 mm`, por lo que los 20 mm libres se verifican. La dirección de salida del eje es `+Z` del CAD nativo, independiente del eje de robot donde se coloque.

La clasificación final de investigación es **B: CAD de familia verificado para representación visual**, para la carcasa y features de montaje de cada variante de freno. Conserva el tamaño de fabricante y reconoce explícitamente el chavetero distinto y la incertidumbre de medida longitudinal. No justifica cambios de controlador, límites, masa, física, colisiones o parentado. Las longitudes manuales siguen sin estar verificadas contra los mismos extremos; la clase B visual no constituye un layout mecánico exacto de la máquina real.
