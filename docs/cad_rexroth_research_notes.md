# Bosch Rexroth R036037003 / CKK 12-90

Consulta: 2026-09-29 en Argentina / 2026-09-30 UTC. Resultado: no se obtuvo un STEP descargable sin correo o cuenta. Se conservaron un catálogo oficial actual y un manual Bosch legacy hospedado por CMA/Flodyne/Hydradyne, con procedencias diferenciadas. No se integró CAD Rexroth en Webots.

## Identidad de la pieza fotografiada

En `docs/reference_previews/IMG_0279.jpg` se lee **MNR R036037003**, **SYN R036030000**, **CS 1004752497 /20**, **FD 005**. La misma placa y el bloque de montaje de cuatro tornillos aparecen en el travesaño horizontal de `IMG_0278.jpg`. Ese travesaño sostiene Z y está montado sobre el carro del módulo longitudinal de base: corresponde a **X**, con confianza alta como inferencia de contexto fotográfico y de la jerarquía validada, no como rotulación explícita del fabricante.

`IMG_0276.jpg` muestra otro material: **MNR R055712186**, SYN R036030000, CS 1004752497 /40, FD 005. Su ubicación bajo el bloque negro y junto a la herramienta coincide con el módulo vertical de `IMG_0277.jpg`: **Z probable**, por contexto. No es evidencia de que Y o Z lleven R036037003.

El manual Bosch **R320103982 (2009.08), páginas 8–9**, muestra exactamente esta disposición de placa y define MNR como número de material/ordering code del Compact Module; SYN como número de serie; CS como pedido del cliente; FD como fecha de fabricación. El dibujo numerado está preservado en `cad/reports/rexroth_legacy_manual_page8.png`. La ficha moderna R036030000 usa ese número como producto base CKK-090-NN-1; su coincidencia con el texto del campo SYN de las fotos **no demuestra una clave completa de configuración ni permite sustituir MNR por SYN**. El valor FD 005 no se transformó en una fecha por falta de regla oficial de decodificación.

R036037003 es, por la placa, un identificador de material/pedido del módulo montado. No se encontró una ficha primaria que decodifique para ese MNR la longitud, carrera, carro, paso del husillo, attachments o edición. La identificación CKK12-90 proviene del pedido del usuario y se corrobora sólo como pista en un listado comercial no primario; no se elevó a identificación exacta de CAD. No se afirmó que R036037003 sea únicamente perfil, carro, base material o configuración completa decodificada.

## Fuentes consultadas y archivos preservados

- [Documentación y recursos oficiales de movimiento lineal](https://www.boschrexroth.com/en/us/c/documentation-and-resources-linear-motion-technology/): enlaza el catálogo de módulos compactos.
- [Página oficial del catálogo](https://www.boschrexroth.com/en/us/media-details/e8278bcd-f4c8-4191-814e-9e557f6c5f27) y [PDF original oficial](https://www.boschrexroth.com/media/e8278bcd-f4c8-4191-814e-9e557f6c5f27): archivo `cad/source/rexroth/EN_CKx_R999000499_2025_05_01_10_2025.pdf`, 33.397.427 bytes. Edición impresa R999000499/2025-05; el portal indica fecha 2025-10-01. SHA256 `E4E120C2C9C051037A9C90B91B09A6BF2CB81273E2A7846C054BD01E71C12DE1`.
- [Manual Bosch legacy R320103982 de 2009.08, copia CMAFH](https://www.cmafh.com/WebsiteCatalog/Data%20Sheets/BRL-LT%20CKK%20CKR/Rexroth%20Instructions%20for%20Compact%20Modules%20CKK%20R320103982%202009_08.pdf): autor Bosch Rexroth; **host no oficial Bosch**. Archivo `cad/source/rexroth/R320103982_2009_08_CMAFH.pdf`, 7.352.030 bytes; SHA256 `21B46183B423CDE12F139644DAE1E867150A06AB7C69BADE3915F54CF5FAE7A2`. Se utilizó para nomenclatura legacy y lectura de placas, no como CAD ni prueba de variante exacta.
- [Herramientas y configuradores oficiales](https://www.boschrexroth.com/en/in/service-and-support/econfigurators-and-tools/) y [eConfigurator CKK/CKR público](https://www.boschrexroth.com/ics/ref/config?c=ar&language=en&matno=R036_CKx).
- [Producto base moderno R036030000](https://www.boschrexroth.com/en/au/p/compact-module-r036030000/): encabezado oficial CKK-090-NN-1; no ficha exacta R036037003.
- [Catálogo Bosch Rexroth en PARTcommunity/3Dfindit](https://boschrexroth.partcommunity.com/3d-cad-models/?info=bosch_rexroth_mcd%2Flinear_motion_technology%2Fcompact_modules%2Fckk) y [familia CKK configurable](https://boschrexroth.partcommunity.com/3d-cad-models/ckk-compact-module-with-ball-screw-assembly-bosch-rexroth?info=bosch_rexroth_mcd%2Flinear_motion_technology%2Fcompact_modules%2Fckk%2Fckk_asmtab.prj): portal del fabricante servido por CADENAS; catálogo marcado 2026-05-05.
- [TraceParts, producto CKK del fabricante](https://www.traceparts.com/tr/product/bosch-rexroth-lineartechnik-compact-modules-ckk-with-ball-screw-drive-and-double-ball-rail-guiding?CatalogPath=BOSCH_LINEAR%3ABOSCH_LINEAR_2023_060_010&Product=90-19042023-058074): el resultado del producto indica **No CAD available**; los formatos STEP publicitarios del pie no son un archivo disponible de esa pieza.

No se encontró licencia abierta específica para estos documentos/CAD. Se conservan el copyright y la procedencia del fabricante; no se infieren derechos de redistribución externa. Uso previsto: consulta técnica y representación local académica. Los originales descargados no se sobrescribieron ni modificaron.

## Comparación dimensional y longitud configurable

El manual legacy, p.8, define la sección de **CKK12-90 como A=90, H=40 mm**. El catálogo actual, pp.14–15 y dibujo p.52, mantiene **CKK-090: A=90, H=40, H1=56 mm**. H1 es la altura superior del conjunto representado en ese dibujo; H mide el cuerpo. La variante del carro y de la connection plate real no está confirmada. La imagen del dibujo se conserva en `cad/reports/rexroth_catalog_page52.png`. Para la familia actual el muñón OF01 es Ø8 mm, sobresale L1=20 mm; L del dibujo actual incluye el cuerpo y los extremos, pero no ese muñón. Los esquemas introductorios legacy no se utilizaron para inferir un datum longitudinal exacto de la pieza real.

| Medida real suministrada | Control de familia CKK090 | Interpretación |
| --- | --- | --- |
| X: 815 × 110 × 55 mm | cuerpo 90 × 40; con carro H1=56 | La sección de cuerpo difiere 20 y 15 mm. H1=56 se acerca a 55, pero falta confirmar si la medición incluía el carro. No prueba coincidencia. |
| Y: 710 × 42 × 93 mm | sección rotada 40 × 90 | Diferencias 2 y 3 mm; cercanía dimensional solamente. MNR de Y no identificado. |
| Z: 355 × 95 × 40 mm | sección rotada 90 × 40 | Diferencias 5 y 0 mm; cercanía dimensional solamente. La foto probable Z tiene otro MNR. |

CKK110 actual ofrece A=110, H=50, H1=66, pero no se eligió para X por una coincidencia aislada de ancho: contradice una asignación automática CKK12-90 y tampoco verifica el MNR fotografiado.

El catálogo y el configurador **actuales** permiten CKK090 de longitud configurable hasta **Lmax=750 mm**; esto **no demuestra un límite del R036037003 legacy**. La medida X815 supera ese máximo actual en 65 mm, pero los puntos de medición reales no están fijados. No se atribuyeron esos 65 mm a un adaptador, motor u otra pieza sin evidencia. La longitud distinta por sí sola no descarta un CAD de familia: la sección, el carro, los extremos y el attachment requieren verificación independiente. No se escala anisotrópicamente un assembly para adaptarlo a las medidas.

## Intento concreto de obtención CAD

Se completó el eConfigurator oficial sin login con **CKK-090, L750, OF01, guía001, LSS, husillo001 12×5/Ø8, carro001 Lca35, relación1, interfaz0, attachment000, motor000, cubierta002, sin sensores/canaleta/enchufe, documentación001 y carro centrado0**. Estas opciones son un candidato de comparación elegido deliberadamente y **no están verificadas contra la máquina**. El configurador generó **MNR R030537116**, distinto de R036037003, y nombre de modelo `CKK_090_NN_1_750_mm_OF01_001_001_001_000`.

`Request CAD model` abrió una ventana con 3D CAD seleccionado, formatos **STEP/PDF3D**, 2D DXF opcional, y un campo obligatorio de **email al que enviar los documentos**. No ofreció un enlace directo de archivo. No se ingresó ni envió correo.

Como alternativa puntual se abrió el CKK de PARTcommunity del fabricante. La vista pública mostró opciones y preview; su selección inicial era CKK110 L140 y **no se descargó ni confundió con CKK090**. Al pulsar `Generar CAD`, el portal redirigió a [SSO de PARTcommunity](https://boschrexroth.partcommunity.com/3d-cad-models/sso/?cwid=7888), con correo comercial, login/registro y proveedores de autenticación. No había sesión utilizable; no se creó cuenta. Esta es una limitación comprobada de acceso a exportación, no una afirmación de que no exista CAD en el fabricante.

## Clasificación y decisión

**A (CAD exacto): ninguno. B (CAD de familia verificado visualmente): ninguno para Rexroth. C: candidato moderno CKK090 L750, no descargado y sin compatibilidad suficiente para integrar. D: ninguna geometría externa incorporada; se conserva el modelo previo.**

La ausencia de CAD local y la incertidumbre de sección, carro, MNR legacy y puntos de medida impiden reemplazar visuales como exactos o familia verificada. Quedan documentados los enlaces y el candidato para una futura comparación cuando se disponga de exportación y de una medición de cuerpo/carriage con datums claros. Se dejó intacta la cinemática y no se reconstruyó el módulo a partir de suposiciones.
