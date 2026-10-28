# Etapa 2B: investigación de CAD de fabricante

La investigación consigue dos CAD oficiales Beckhoff de la familia AM3023 y verifica su geometría con el plano del fabricante. La carcasa de la variante con freno se incorpora como visual del servo Z. **Son CAD de familia, clase B; no son STEP del part number exacto de la máquina.** El piloto LiDAR de X se conserva. También se conserva un STEP oficial AX5203 como candidato C, preparado para una etapa de gabinete. Para Rexroth se verifican documentos y configuradores, pero no se obtiene un STEP local A/B: las exportaciones comprobadas requieren email o autenticación y la configuración legacy sigue sin decodificarse.

Consulta inicial: 29 de septiembre de 2026, Argentina; registros UTC del 30 de septiembre de 2026. Los originales descargados se guardan sin edición en `cad/source/`; los hashes completos se registran en [cad_sources.json](E:/ROBOTICA/CARTESIANO/cad/reports/cad_sources.json). Se usan localmente para este proyecto académico, sin publicación externa.

## Fuentes primarias y procedencia

| Fuente | Qué permite comprobar |
| --- | --- |
| [Repositorio técnico oficial AM30xx de Beckhoff](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AM30xx) | ZIP STEP para `AM3023-1xx0` y `AM3023-1xx1` |
| [Página oficial AM3023](https://www.beckhoff.com/en-en/support/service-products/motion-service-products/am3023-wcyz-000a.html) | Familia de motor y variantes |
| [Manual oficial AM3000/AM3500, versión 1.5](https://download.beckhoff.com/download/Document/motion/am3000_am3500_ba_en.pdf) | Nomenclatura y plano AM302x de la página 41 |
| [Condiciones de uso de Beckhoff](https://www.beckhoff.com/en-en/terms-of-use/) | Procedencia y restricciones de uso; no se encontró licencia CAD abierta específica |

No se utilizaron modelos comunitarios sin identificación. La disponibilidad pública del archivo no se presenta como autorización de redistribución. El ZIP original y el STEP extraído permanecen en `cad/source/beckhoff/`; la conversión trabaja sobre derivados.

## Identificación AM3023 y alcance de la clase B

La nomenclatura documentada es `AM30uv-wxyz-000a`. El código `u=2` indica flange de 58 mm; `v=3`, longitud de motor 3; `w=0`, eje liso; `w=1`, chavetero; `x=C`, bobinado C; `y=4`, encoder BiSS multiturno; `z=0`, sin freno; `z=1`, freno de mantenimiento de 24 V; `a=0`, conectores acodados giratorios. Estos significados provienen del manual, no de una interpretación del nombre del ZIP. [Manual Beckhoff](https://download.beckhoff.com/download/Document/motion/am3000_am3500_ba_en.pdf).

| Part number fotografiado | CAD oficial encontrado | Clase y limitación |
| --- | --- | --- |
| `AM3023-0C40-0000` | `AM3023-1xx0.step` | **B: misma familia, geometría verificada**. Carcasa sin freno y fijación comprobadas; STEP con chavetero frente al eje liso del equipo; bobinado/encoder genéricos en el nombre |
| `AM3023-0C41-0000` | `AM3023-1xx1.step` | **B: misma familia, geometría verificada**. Carcasa con freno y fijación comprobadas; misma diferencia de eje y placeholders |

No se obtuvo un CAD clase A del part number completo. La clase B se refiere a carcasa, flange, centrador, diámetro de eje, fijaciones y longitud de la variante con/sin freno. No acredita la pose exacta de montaje ni un match completo de la máquina.

La fotografía `IMG_0275` muestra `AM3023-0C41-0000`, `Br. 24 VDC` y `+EXT -13M1` en un motor vertical. Su asignación a Z es una inferencia visual de confianza alta, apoyada en las vistas generales. `IMG_0280` muestra `AM3023-0C40-0000`, `+EXT -9M1`, horizontal; esa vista no resuelve de manera inequívoca si corresponde a X o Y. Por eso sólo se sustituye el visual de Z y no se replica el mismo STEP indiscriminadamente en los tres ejes.

## Verificación geométrica del STEP

Los dos STEP declaran milímetros y fueron exportados mediante SolidWorks 2008 / SwSTEP 2.0. OpenCascade reconoce un sólido válido en cada archivo, con 615 caras sin freno y 623 con freno. El plano de montaje frontal nativo está en Z = -0.8 mm; el eje sale hacia +Z en las coordenadas originales.

| Característica | Plano oficial | Medición CAD | Resultado |
| --- | ---: | ---: | --- |
| Flange | 58 × 58 mm | 58 × 58 mm | Compatible |
| Centrado principal | Ø40 mm | Ø40 mm | Compatible; el chaflán no define el diámetro nominal |
| Eje | Ø9 × 20 mm libres | Ø9; 20 mm desde plano frontal a extremo | Compatible en tamaño; chavetero distinto al target |
| Agujeros | 4 × Ø4.8 mm | 4 × Ø4.8 mm | Compatible |
| Círculo de agujeros | Ø63 mm | Ø63 mm | Compatible; centros X/Y = ±22.2738636 mm |
| Cuerpo sin freno | 133.4 mm | 133.4 mm entre flange y extremo trasero | Compatible |
| Cuerpo con freno | 167.5 mm | 167.5 mm entre flange y extremo trasero | Compatible |
| Protrusión de conectores | 39 mm sobre cuerpo | Bbox transversal 58 × 97 mm | Compatible |

El envelope nativo completo es **58 × 97 × 153.4 mm** sin freno y **58 × 97 × 187.5 mm** con freno. El eje de longitud corresponde al Z del CAD, distinto del eje Z del robot. El envelope incluye conectores y eje libre; la sección de carcasa es 58 × 58 mm. Reportes: [mediciones](E:/ROBOTICA/CARTESIANO/cad/reports/am3023_cad_measurements.json), [features de fijación](E:/ROBOTICA/CARTESIANO/cad/reports/am3023_mounting_features.json) y [verificación de fuentes](E:/ROBOTICA/CARTESIANO/cad/reports/beckhoff_research.json).

## Comparación con las medidas manuales

Se calcula `delta = CAD − medida manual` y `% = 100 × delta / medida manual`. Las medidas manuales son aproximadas y sus puntos extremos no fueron documentados. El ancho de la carcasa se compara con 60 mm; el envelope con conectores se registra aparte y no se confunde con esa sección.

| Motor / característica | CAD | Real aproximado | Delta | Delta % | Conclusión |
| --- | ---: | ---: | ---: | ---: | --- |
| AM3023, ancho flange/carcasa | 58 mm | 60 mm | -2 mm | -3.33 % | Cercano a medida aproximada |
| AM3023, alto carcasa | 58 mm | 60 mm | -2 mm | -3.33 % | Cercano; conectores elevan envelope a 97 mm |
| Sin freno, total axial con eje | 153.4 mm | 200 mm X/Y | -46.6 mm | -23.30 % | Diferencia grande; requiere medir los mismos extremos |
| Con freno, total axial con eje | 187.5 mm | 240 mm Z | -52.5 mm | -21.875 % | Diferencia grande; requiere medir los mismos extremos |

No se atribuye la discrepancia a un adaptador, soporte o cable sin evidencia. Tampoco se alarga el CAD para llenar la primitiva anterior de 200/240 mm. La integración conserva tamaño de fabricante y deja documentada esta limitación. [Comparación estructurada](E:/ROBOTICA/CARTESIANO/cad/reports/cad_comparison.json).

## Rexroth R036037003 / CKK 12-90

Se consultaron la [documentación oficial de movimiento lineal](https://www.boschrexroth.com/en/us/c/documentation-and-resources-linear-motion-technology/), el [catálogo oficial de módulos compactos R999000499/2025-05](https://www.boschrexroth.com/media/e8278bcd-f4c8-4191-814e-9e557f6c5f27), el [eConfigurator CKK/CKR](https://www.boschrexroth.com/ics/ref/config?c=ar&language=en&matno=R036_CKx), el catálogo de fabricante en [PARTcommunity/CADENAS](https://boschrexroth.partcommunity.com/3d-cad-models/ckk-compact-module-with-ball-screw-assembly-bosch-rexroth?info=bosch_rexroth_mcd%2Flinear_motion_technology%2Fcompact_modules%2Fckk%2Fckk_asmtab.prj) y el producto de fabricante en [TraceParts](https://www.traceparts.com/tr/product/bosch-rexroth-lineartechnik-compact-modules-ckk-with-ball-screw-drive-and-double-ball-rail-guiding?CatalogPath=BOSCH_LINEAR%3ABOSCH_LINEAR_2023_060_010&Product=90-19042023-058074). No se obtuvo STEP local. TraceParts indicaba ausencia de CAD en ese producto; los portales que sí generaban CAD requerían envío por email o login/registro.

Se preserva el catálogo actual en `cad/source/rexroth/EN_CKx_R999000499_2025_05_01_10_2025.pdf` (33 397 427 bytes), edición impresa 2025-05 y fecha del portal 2025-10-01. También el [manual Bosch R320103982 de 2009.08, copia alojada por CMAFH](https://www.cmafh.com/WebsiteCatalog/Data%20Sheets/BRL-LT%20CKK%20CKR/Rexroth%20Instructions%20for%20Compact%20Modules%20CKK%20R320103982%202009_08.pdf) (7 352 030 bytes): autor fabricante, **host no oficial Bosch**, diferenciados en el manifiesto. Sirve para campos de placa y familia legacy, no como prueba de un CAD exacto.

`IMG_0279` identifica **MNR R036037003**. Por la placa, bloque de cuatro tornillos y contexto `IMG_0278`, corresponde a **X**, con confianza alta como inferencia fotográfica. `IMG_0276` muestra otro MNR, **R055712186**, asignado a **Z probable** por contexto `IMG_0277`. El manual legacy define MNR como identificador de material/pedido del Compact Module; no se encontró una ficha primaria que descifre las opciones del R036037003. **SYN** es el campo de número de serie: el `R036030000` visible en ese campo no se sustituye por el MNR aunque exista un producto base moderno con ese número. FD 005 no se decodificó a una fecha sin regla probada.

| Control de familia | Real aproximado | Diferencia y conclusión |
| --- | --- | --- |
| CKK12-90 legacy / CKK090 actual, cuerpo 90 × 40 mm | X, sección 110 × 55 mm | -20/-15 mm (-18.18/-27.27 %); extremos de medición no homologados |
| CKK090 actual, altura superior del conjunto del plano H1 = 56 mm | X, alto 55 mm | +1 mm (+1.82 %); variante real de carro/placa y datum sin confirmar |
| Candidato moderno L = 750 mm | X, largo 815 mm | -65 mm (-7.98 %); longitud configurable y datums distintos no prueban incompatibilidad legacy |
| Cuerpo de familia rotado 90 × 40 mm | Y, sección 93 × 42 mm | -3/-2 mm; cercanía dimensional sin MNR de Y |
| Cuerpo de familia rotado 90 × 40 mm | Z, sección 95 × 40 mm | -5/0 mm; foto probable Z muestra MNR diferente |

La longitud máxima estándar **750 mm** pertenece al catálogo/configurador **actual CKK090**, no se prueba como límite del R036037003 legacy. Tampoco se selecciona CKK110 por coincidir sólo con el ancho 110 mm. La longitud distinta por sí sola no descarta un CAD: sección, carro, tapas, husillo y attachment deben comprobarse por separado.

Se completó deliberadamente un candidato moderno **CKK090 L750 OF01**, sin motor/attachment ni sensores, con opciones registradas en `rexroth_research.json`. El configurador produjo **MNR R030537116**, diferente del target, y formatos STEP/PDF3D. Se clasifica **C: candidato de familia insuficientemente confirmado**, sin archivo local ni geometría convertida. El diálogo exigía un email para entregar los documentos y PARTcommunity redirigía a SSO; no se suministró correo ni se creó cuenta. Esta limitación de acceso no significa que el fabricante carezca de CAD.

No se obtuvo A ni B Rexroth y **no se integra ningún CAD Rexroth**. El scan X y las primitivas se conservan. No se escala longitudinalmente todo un assembly ni se inventa un adaptador para explicar diferencias. Una futura adaptación podría alterar sólo la extrusión central tras comprobar la sección, preservando carro, tapas, motor y fijaciones.

Evidencia detallada: [reporte Rexroth](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_research.json), [notas de investigación](E:/ROBOTICA/CARTESIANO/docs/cad_rexroth_research_notes.md), [placa y geometría legacy](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_legacy_manual_page8.png) y [dibujo de familia actual](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_catalog_page52.png).

## Componentes de gabinete y límites de alcance

La búsqueda opcional acotada del **AX5203** obtiene un ZIP y STEP oficiales del [repositorio AX5000 de Beckhoff](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AX5000/AX5203_stp.zip). El STEP fue exportado el 4 de marzo de 2008 mediante Autodesk Inventor 2008, con identificador interno `AX-2Kanal-ohne-Modul`. El modelo base es AX5203, pero no acredita el sufijo eléctrico ni revisión de las dos unidades de la máquina.

Se clasifica **C: aproximación/candidato oficial pendiente de compatibilidad**. La [ficha vigente AX5203](https://www.beckhoff.com/en-en/products/motion/servo-drives/ax5000-digital-compact-servo-drives/ax5203.html) publica ancho 92, profundidad 232 y alto 274 mm, excluyendo conectores. El envelope nativo STEP completo es aproximadamente **92.760 × 245.800 × 356.738 mm**; no es una comparación de extremos homologados. No se interpreta automáticamente la diferencia como revisión incompatible, ni se declara equivalencia exacta. Se requiere reconciliar estado del CAD, conectores y revisión antes de integrarlo.

La conversión produce un OBJ nativo de **151 990 triángulos / 15 319 742 bytes**, un sólido y 4 320 caras CAD, con deflexión **0.3 mm / 15°**. Queda en `cad/converted/ax5203_native.obj`. Se añade a la biblioteca Blender como `BECKHOFF_AX5203/AX5203_OFFICIAL_LIBRARY_CLASS_C` reducido a **30 000 triángulos / 36 661 vértices** (-80.26 %). El bbox visual es aproximadamente 92.789 × 245.828 × 356.761 mm, con variación inferior a 0.03 mm por dimensión frente al OBJ nativo.

Se conservan XYZ nativos, metros, rotación identidad y escala 1. La ubicación Y +0.5 m sirve sólo para separar modelos en la biblioteca; no representa un montaje de gabinete. No se exporta este candidato a `meshes/cad/` ni se incorpora al robot o gabinete. El archivo `.blend` final ocupa **2 368 268 bytes**, conserva los modelos AM3023 y las seis Collections previas; los tres OBJ de Z mantienen sus hashes. [Reporte AX5203](E:/ROBOTICA/CARTESIANO/cad/reports/ax5203_research.json), [preparación Blender](E:/ROBOTICA/CARTESIANO/cad/reports/ax5203_blender_processing.json).

C6925, EK1100, EL1008 y EL2008 no se investigaron en profundidad: se mantiene la prioridad mecánica indicada. Sus Collections están preparadas en el archivo Blender, pero una Collection vacía no significa que exista un CAD descargado o convertido.

## Herramientas y resultados de preparación

Se inspeccionó PATH y las carpetas habituales de instalación. No se hallaron FreeCAD/FreeCADCmd, CAD Assistant ni Assimp en ese alcance. Se usó **OpenCascade 7.9.3.1**, bindings `cadquery-ocp-novtk 7.9.3.1.1`, aislados en `.tools/cad_reader`; wheel de aproximadamente 46 MB y entorno de 158 766 250 bytes. No se instaló una aplicación CAD grande. Blender **5.2.2 LTS** importa los OBJ convertidos, no los STEP directamente.

La teselación utiliza deflexión lineal absoluta **0.2 mm** y angular **12°**, sin caras faltantes. Resultan 50 452 triángulos sin freno y 49 534 con freno. Blender reduce a **15 000 / 14 999** triángulos, conservando la silueta visual y el tamaño; no es una mesh para fabricación ni para medir microfeatures después de Decimate. Véase [cad_integration.md](E:/ROBOTICA/CARTESIANO/docs/cad_integration.md).
