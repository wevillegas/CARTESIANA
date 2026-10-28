# Reporte de etapa 2B: CAD de fabricante

Se descargaron y verificaron dos STEP oficiales de la familia Beckhoff AM3023. Se integra **un servo Z con freno como clase B**, manteniendo el modelo híbrido y el piloto escaneado de X. No se obtuvo un STEP exacto de `AM3023-0C40-0000` ni `AM3023-0C41-0000`. AX5203 queda como biblioteca C. Rexroth se investigó y comparó mediante documentos/configurador, sin STEP local A/B ni integración. Las pruebas aprueban y no se detectaron regresiones.

## 1. Fuentes consultadas

Repositorio técnico Beckhoff AM30xx y AX5000, páginas AM3023 y AX5203, manual AM3000/AM3500 versión 1.5 y condiciones de uso oficiales; documentos y eConfigurator Bosch Rexroth, catálogo de fabricante PARTcommunity/TraceParts y manual Bosch legacy alojado por CMAFH; fotografías locales y reportes BRep/métricas de etapas 1/2. [Investigación](E:/ROBOTICA/CARTESIANO/docs/cad_research.md).

## 2. URLs de fabricante

- [Repositorio STEP AM30xx](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AM30xx).
- [Producto AM3023](https://www.beckhoff.com/en-en/support/service-products/motion-service-products/am3023-wcyz-000a.html).
- [Manual AM3000/AM3500](https://download.beckhoff.com/download/Document/motion/am3000_am3500_ba_en.pdf).
- [Condiciones de uso Beckhoff](https://www.beckhoff.com/en-en/terms-of-use/).
- [STEP oficial AX5203](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AX5000/AX5203_stp.zip) y [ficha de producto](https://www.beckhoff.com/en-en/products/motion/servo-drives/ax5000-digital-compact-servo-drives/ax5203.html).
- [Catálogo oficial Rexroth R999000499/2025-05](https://www.boschrexroth.com/media/e8278bcd-f4c8-4191-814e-9e557f6c5f27), [eConfigurator CKK](https://www.boschrexroth.com/ics/ref/config?c=ar&language=en&matno=R036_CKx) y [catálogo CADENAS del fabricante](https://boschrexroth.partcommunity.com/3d-cad-models/ckk-compact-module-with-ball-screw-assembly-bosch-rexroth?info=bosch_rexroth_mcd%2Flinear_motion_technology%2Fcompact_modules%2Fckk%2Fckk_asmtab.prj).

## 3. Modelos encontrados

`AM3023-1xx0`, familia sin freno, y `AM3023-1xx1`, familia con freno. Ambos tienen chavetero; los motores fotografiados `0C40/0C41` son variantes de eje liso. Los nombres `xx` no confirman encoder ni bobinado exactos. AX5203 oficial histórico, exportado en 2008, sin sufijo/revisión de máquina confirmados. No se presenta ningún modelo como match A.

Rexroth: candidato configurable moderno CKK090 L750 OF01, MNR generado **R030537116**, distinto de **R036037003**. No se descargó su STEP: entrega por email en eConfigurator / SSO en PARTcommunity. La foto asigna R036037003 a X por contexto; probable Z tiene R055712186. No se decodificó la configuración legacy exacta.

## 4. Archivos descargados

| Archivo en `cad/source/beckhoff/` | Bytes |
| --- | ---: |
| `am3023-1xx0_stp.zip` | 446 884 |
| `AM3023-1xx0.step` extraído | 2 477 003 |
| `am3023-1xx1_stp.zip` | 453 078 |
| `AM3023-1xx1.step` extraído | 2 583 682 |
| `am3000_am3500_ba_en.pdf` | 3 578 630 |
| `AX5203_stp.zip` | 1 225 770 |
| `AX5203.stp` extraído | 7 931 005 |

Los originales no se sobrescriben. El proyecto conserva `backups/stage1_validated` y el checkpoint previo al CAD `backups/stage2_validated`, de 90 archivos. La verificación final de sus manifests aprueba todos los archivos registrados de ambos backups. No hay repositorio Git inicializado.

En `cad/source/rexroth/`: catálogo `EN_CKx_R999000499_2025_05_01_10_2025.pdf`, **33 397 427 bytes**, host oficial Bosch; manual Bosch legacy `R320103982_2009_08_CMAFH.pdf`, **7 352 030 bytes**, autor oficial y host CMAFH no oficial. No se descargó ZIP/STEP Rexroth.

## 5. SHA256

| Archivo | SHA256 |
| --- | --- |
| ZIP sin freno | `4fa845f53c9fe9237f3b6f1bf993fc7953542d94bd74c423898a5a401bd87749` |
| STEP sin freno | `d35f2877596c5495a2905be1c80671cca097cea173db05a0ac7d88bbeda2cd35` |
| ZIP con freno | `f9d1998738c678429f493ebae884a4358aafc864e5f287ce3d2943af03844669` |
| STEP con freno | `c1b03dbfbdc256f13e44f4d73003205d634f8bbb695bae4cf5645af41cad281e` |
| Manual | `eab989658d9d810374f07da8292285bc43f7e437d0b4500b5750e746d7a92bf6` |
| ZIP AX5203 | `03939da646c305c59f038d350f4aad20d2548a729f285ba6ac804f9d0c3fc2a5` |
| STEP AX5203 | `217b6d3acd91b67a3c8e7f7d305bf3588f33a95b8b348477bcf3540f3a7ea58d` |
| Catálogo Rexroth actual | `e4e120c2c9c051037a9c90b91b09a6bf2cb81273e2a7846c054bd01e71c12de1` |
| Manual Rexroth legacy, copia CMAFH | `21b46183b423cde12f139644dae1e867150a06ab7c69bade3915f54cf5fae7a2` |

El [manifiesto de fuentes](E:/ROBOTICA/CARTESIANO/cad/reports/cad_sources.json) contiene hashes y URLs por archivo; los reportes de conversión comprueban que los STEP permanecen iguales tras lectura.

## 6. Formatos

Origen ZIP, STEP AP214 en milímetros y PDF. Derivados OBJ/MTL en metros y `.blend`; Webots usa OBJ triangulado y apariencias nativas por color. No se importa STEP directamente en Blender ni se usa mesh CAD para colisión.

## 7. Clasificación A/B/C/D

| CAD | Clase | Alcance |
| --- | --- | --- |
| AM3023-1xx0 | **B** | Carcasa y montaje de familia sin freno verificados; diferencias de eje y part number |
| AM3023-1xx1 | **B** | Carcasa y montaje de familia con freno verificados; diferencias de eje y part number |
| AX5203 | **C** | Oficial del modelo base; revisión/sufijo y envelope histórico vs ficha actual no reconciliados |
| CKK090 L750 OF01, MNR R030537116 | **C, no descargado** | Opciones modernas elegidas para comparar; no configuración ni geometría verificada del R036037003 |

No se obtuvo A ni un B Rexroth. No se descargó ni utilizó un CAD D. Los PDF son documentación, no modelos CAD y no reciben clase A/B/C/D.

## 8. Dimensiones CAD

Flange 58 × 58 mm, centrador Ø40 mm, eje Ø9 × 20 mm libres, cuatro agujeros Ø4.8 mm sobre PCD Ø63 mm. Cuerpo axial 133.4/167.5 mm sin/con freno. Envelope completo con eje y conectores **58 × 97 × 153.4/187.5 mm**. Los 97 mm incluyen 39 mm de protrusión de conectores. AX5203 nativo completo: **92.760 × 245.800 × 356.738 mm**; no homologado con ancho/profundidad/alto de ficha sin conectores. [Features medidos](E:/ROBOTICA/CARTESIANO/cad/reports/am3023_mounting_features.json).

Rexroth documental: CKK12-90 legacy y CKK090 actual tienen sección de cuerpo **90 × 40 mm**; H1 **56 mm** es la altura superior del conjunto representado en el plano. La variante real de carro/placa no está confirmada. Candidato elegido L750; máximo estándar actual 750 mm, sin probar límite legacy. No hay bbox de mesh Rexroth local.

## 9. Medidas reales de comparación

Servos X/Y aproximadamente 200 × 60 × 60 mm; servo Z aproximadamente 240 × 60 × 60 mm. Módulo X 815 × 110 × 55 mm, Y 710 × 42 × 93 mm y Z 355 × 95 × 40 mm. Medidas manuales aproximadas; los extremos axiales medidos no están identificados.

## 10. Diferencias

Flange/carcasa: -2 mm por dimensión frente a 60 mm (-3.33 %). Total axial sin freno frente a 200 mm: -46.6 mm (-23.30 %). Total axial con freno frente a 240 mm: -52.5 mm (-21.875 %). Las discrepancias de longitud son grandes y quedan abiertas a nueva medición; no se atribuyen a un adaptador no documentado. AX5203 no tiene medidas manuales de máquina; la ficha 92 × 232 × 274 mm excluye conectores, de modo que no se calcula un delta engañoso contra el envelope completo. [Comparación JSON](E:/ROBOTICA/CARTESIANO/cad/reports/cad_comparison.json).

Rexroth X: cuerpo de familia 90 × 40 vs 110 × 55 mm manual, -20/-15 mm (-18.18/-27.27 %); H1=56 vs 55, +1 mm (+1.82 %). L750 vs 815, -65 mm (-7.98 %). Los datums no están homologados; no se descarta sólo por longitud ni se afirma que un adaptador explique la diferencia. Las secciones rotadas de Y/Z se acercan a la familia, pero no prueban identidad.

## 11. Herramientas STEP → mesh

Inspección de conversores instalados, Python 3.12.14 y OpenCascade 7.9.3.1 mediante `cadquery-ocp-novtk 7.9.3.1.1` aislado en `.tools/cad_reader`; Blender 5.2.2 LTS background y Webots R2025a. No se instaló FreeCAD ni otra aplicación grande. Teselación AM3023 con deflexión **0.2 mm / 12°** y AX5203 con **0.3 mm / 15°**, ambas con escala uniforme 0.001 para mm→m. [Entorno](E:/ROBOTICA/CARTESIANO/cad/reports/conversion_environment.json).

## 12. Meshes generadas

`cad/converted/am3023_no_brake_native.obj`, `cad/converted/am3023_brake_native.obj`, modelos optimizados en `blender/official_cad_components.blend` y tres OBJ de materiales del servo Z en `meshes/cad/`. La exportación local de Z tiene flange en `(0,0,0.1775)` m, eje -Z, cuerpo +Z y conectores +Y. AX5203 conserva `cad/converted/ax5203_native.obj` y se añade a su Collection Blender; no se exporta ni integra en Webots. La biblioteca final ocupa **2 368 268 bytes**.

## 13. Número de polígonos

Un sólido BRep por variante, 615/623 caras CAD. Teselación 50 452/49 534 triángulos; Blender 15 000/14 999 (-70.27 %/-69.72 %). Visual Z: 1 306 + 6 664 + 7 029 = **14 999 triángulos**, **1 141 125 bytes**. AX5203: un sólido, 4 320 caras y 151 990 triángulos / 15 319 742 bytes de OBJ nativo; biblioteca Blender **30 000 triángulos / 36 661 vértices** (-80.26 %). Es una preparación para visualización, no geometría de fabricación.

## 14. Componentes integrados en Webots

Sólo el visual del servo Z con freno, bajo `Z_MODULE`, usando AM3023-1xx1 de familia clase B. Mantiene pose visual local de identidad y escala 1. Se retira únicamente su primitiva visual. El tamaño es de fabricante y no se estira hasta los 240 mm manuales.

## 15. Componentes no integrados

Servos X/Y preparados en biblioteca de familia pero aún con primitivas en el robot. Ningún módulo Rexroth integrado: no se obtuvo CAD local A/B. AX5203 preparado sólo como biblioteca de análisis; C6925, EK1100, EL1008 y EL2008 no investigados en profundidad. Mesa, gabinete, carros y herramienta mantienen representación anterior; X conserva el piloto scan.

## 16. Motivo de cada descarte o aplazamiento

No se replica AM3023 sin resolver eje físico y freno de X/Y. No se reemplaza el scan X por Rexroth: MNR legacy sin opciones decodificadas, sección/carro y medidas con datums sin verificar; el candidato moderno tiene MNR diferente y acceso a exportación por email/login. AX5203 es C porque su revisión/sufijo y envelope no están homologados; no se integra automáticamente. El resto del panel tiene menor prioridad y no aporta a la cinemática. No se etiqueta una ausencia de descarga como CAD descartado ni se construye una falsa equivalencia de part number.

## 17. Resultado de validaciones

Invariantes estáticos contra etapa 2 **14/14 PASS**; ejecución CAD Webots **34/34 PASS** (23 originales + 11 complementarias); scan con servo CAD **34/34 PASS**; controlador original final **23/23 PASS**, salida 0 y sin checks fallidos. Logs finales sin errores ni warnings relevantes. [Prueba CAD](E:/ROBOTICA/CARTESIANO/docs/cad_visual_validation.json), [prueba scan](E:/ROBOTICA/CARTESIANO/docs/scan_visual_validation.json), [prueba original](E:/ROBOTICA/CARTESIANO/docs/validation_report.json). La ejecución corregida registra 63.40 s de pared para 258.32 s simulados; no se midió FPS ni tiempo aislado de carga.

Se documenta una corrección del helper PowerShell posterior a la primera prueba aprobada y una corrección del encuadre cercano. [Registro del helper](E:/ROBOTICA/CARTESIANO/cad/reports/validation_helper_notes.md).

## 18. Regresiones

Se conserva el conteo 3/3/3 y el guard detecta cambios protegidos. Las cinco métricas continuas de la ejecución original final son **idénticas al checkpoint etapa 2**: exceso de límite 0.049050 mm, deriva fija 0, diferencia de orientación 0.0000192614, error máximo TCP 0.202497 mm y separación mínima herramienta 0.209748721 m. La simulación recorre los mismos 193.424 s. El cierre aprueba 15/15 referencias y assets scan protegidos, fuentes AM3023 originales y meshes integradas sin cambio; controlador/runtime/parámetros son byte idénticos. **No se detectaron regresiones.** [Comparación final](E:/ROBOTICA/CARTESIANO/cad/reports/regression_comparison.json).

## 19. Capturas

[AM3023 sin freno Blender](E:/ROBOTICA/CARTESIANO/docs/cad_views/am3023_no_brake_blender.jpg), [AM3023 con freno Blender](E:/ROBOTICA/CARTESIANO/docs/cad_views/am3023_brake_blender.jpg), [AX5203 Blender](E:/ROBOTICA/CARTESIANO/docs/cad_views/ax5203_blender.jpg), [servo Z Webots](E:/ROBOTICA/CARTESIANO/docs/cad_views/webots_servo_z_closeup.jpg) y [robot completo](E:/ROBOTICA/CARTESIANO/docs/cad_views/webots_cad_final.jpg), junto a nueve poses de ejes en la misma carpeta. No se inventa una captura Rexroth si no hay CAD fiable.

Rexroth tiene evidencia documental rasterizada: [placa/familia legacy](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_legacy_manual_page8.png) y [plano de familia actual](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_catalog_page52.png). Son páginas de PDF, no vistas de una mesh CAD descargada.

## 20. Paths de archivos importantes

- [Fuentes y hashes](E:/ROBOTICA/CARTESIANO/cad/reports/cad_sources.json).
- [Investigación](E:/ROBOTICA/CARTESIANO/docs/cad_research.md).
- [Integración y comandos](E:/ROBOTICA/CARTESIANO/docs/cad_integration.md).
- [Escena CAD separada](E:/ROBOTICA/CARTESIANO/blender/official_cad_components.blend).
- [Configuración visual CAD](E:/ROBOTICA/CARTESIANO/config/cad_integration.json).
- [Mundo principal](E:/ROBOTICA/CARTESIANO/worlds/cartesian_robot.wbt).
- [Mundo de validación CAD](E:/ROBOTICA/CARTESIANO/worlds/cartesian_cad_validation.wbt).
- [Invariantes](E:/ROBOTICA/CARTESIANO/cad/reports/kinematic_invariants.json).
- [Regresión final](E:/ROBOTICA/CARTESIANO/cad/reports/regression_comparison.json).
- [Inventario de cambios](E:/ROBOTICA/CARTESIANO/cad/reports/change_manifest.json).
- [Reporte Rexroth](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_research.json).
- [Reporte AX5203](E:/ROBOTICA/CARTESIANO/cad/reports/ax5203_research.json).
- [Preparación de biblioteca AX5203](E:/ROBOTICA/CARTESIANO/cad/reports/ax5203_blender_processing.json).

## 21. Recomendaciones para siguiente etapa

Medir cada motor con extremos equivalentes al plano: flange a carcasa trasera y eje libre por separado; fotografiar la etiqueta de cada eje e identificar X/Y/Z; relevar offset y dirección de conectores, montaje y acoplamiento reales. Para Rexroth, fotografiar placa completa, sección, carro, tapas y montaje, y obtener type code/configuración antes de modificar perfil longitudinal. Mantener pruebas cinemáticas y colisiones simples. Inicializar Git puede facilitar futuros cambios; no es requisito ni se realizó automáticamente en esta etapa.
