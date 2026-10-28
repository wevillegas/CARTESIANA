# Análisis de escaneos 3D

La inspección se realizó antes de editar las mallas, con **rhino3dm 8.35.0** y vistas crudas generadas en **Blender 5.2.2 LTS**. Los originales de referencias/ se abrieron en lectura y permanecen intactos. docs/scan_analysis.json conserva el inventario numérico y docs/scan_analysis_base.md el informe inicial reproducible. docs/scan_alignment_candidates.json registra candidatos geométricos de alineación; no son medidas físicas verificadas.

## Inventario por archivo

| Dato | untitled 2.3dm | untitled.3dm |
| --- | --- | --- |
| Tamaño | 7 463 644 bytes | 7 463 712 bytes |
| Formato de archivo 3DM | 80 | 90 |
| Versión informada por el lector | 80 | 90 |
| Aplicación registrada | Rhinoceros 9 WIP / iRhino | Rhinoceros 9 WIP / iRhino |
| Unidades declaradas | Metros | Metros |
| Factor de unidades a metros | 1.0 | 1.0 |
| Tolerancia absoluta del archivo | 0.001 m | 0.001 m |
| Objetos | Una Mesh y una PointCloud | Una Mesh y una PointCloud |
| Mesh: vértices | 16 217 | 16 217 |
| Mesh: polígonos originales | 24 851 | 24 851 |
| Mesh: triángulos tras triangulación | 25 000 | 25 000 |
| UVs de la Mesh | 16 217 | 16 217 |
| Puntos de la nube | 2 775 | 2 775 |
| Materiales y texturas | Un material y una textura embebida | Un material y una textura embebida |

La textura embebida es PNG RGBA de 2048 × 2048 píxeles. Su material conserva una ruta de iOS que no existe en esta computadora; se extrae la imagen a blender/derived/scan_atlas.png y se usa una copia JPEG RGB en textures/scan_atlas.jpg para Webots.

La geometría triangular y las UV de ambas Mesh son idénticas. Los contenedores/formato y metadatos difieren, pero no aportan dos observaciones geométricas complementarias. Se usa untitled 2.3dm como fuente del OBJ derivado y se inspecciona también el segundo archivo; no se superponen las dos Mesh.

## Extremos y bounding boxes

Los siguientes valores son iguales en ambas capturas y corresponden al archivo original, **antes del registro del piloto**, en metros.

| Geometría | Mínimo X, Y, Z | Máximo X, Y, Z | Dimensiones X, Y, Z |
| --- | --- | --- | --- |
| Mesh | [-0.555205, -0.795830, -0.006297] | [0.398178, 0.871380, 1.658526] | [0.953383, 1.667210, 1.664823] |
| PointCloud | [-0.474931, -0.797239, 0.854675] | [0.473940, 0.285171, 1.661507] | [0.948872, 1.082411, 0.806832] |

El bounding box de la Mesh incluye robot, mesa, gabinete y cables. No es el tamaño de un módulo ni debe forzarse a 0.90 × 0.60 × 0.85 m. La nube cubre el conjunto superior y presenta otro registro XY respecto a la Mesh; no se mezcló con sus vértices ni se usó como correspondencia para alinearla.

## Independencia de piezas y calidad

La Mesh fusiona varios cuerpos físicos. Los dos objetos del archivo, Mesh y nube de puntos, son representaciones distintas; no son dos links independientes.

Hay **200 componentes con conectividad por índices**. Al unir posiciones coincidentes a 1 micrómetro, únicamente para analizar topología, quedan **3 componentes**, de 24 554, 368 y 78 triángulos. Las costuras UV separan índices coincidentes, por lo que 200 componentes no significa 200 piezas físicas. Esa unión de análisis no se aplica destructivamente a las UV exportadas.

El lector informa Mesh válida y cerrada, sin triángulos degenerados ni aristas no manifold. Se detectan 7 034 aristas de borde por índices y cero tras la unión de coordenadas para análisis. Estos números no prueban que el scan sea geométricamente fiel: una reconstrucción puede cerrar huecos con paredes ficticias o unir cuerpos próximos mientras sigue siendo topológicamente cerrada.

Las vistas crudas de docs/scan_views/ permiten reconocer la máquina, pero muestran patas/travesaños irregulares, gabinete abierto reconstruido con distorsión y mezcla de guías, carros, cables y apoyos. Los cuerpos móviles no tienen una separación limpia. Los restos pequeños y componentes secundarios no se interpretan automáticamente como piezas útiles ni como ruido sólo por su tamaño.

La textura facilita identificar Rexroth, goma y gabinete, aunque tiene variaciones de exposición y superficies trianguladas claras. La calidad es suficiente para referencia visual y un piloto parcial, no para recuperar dimensiones de carros o una geometría CAD. En la región piloto se retiraron 13 triángulos de seis islas de hasta tres caras, usando conectividad virtual por coordenadas para conservar las costuras UV. Persisten bordes de recorte y huecos propios de una superficie parcial.

## Clasificación mecánica

| Grupo reconocible | Destino | Decisión actual |
| --- | --- | --- |
| Mesa, patas, travesaños, gabinete y soportes | Base estática | Primitivas; orientación de mesa ambigua y gabinete deformado |
| Guía y servo Y | FIXED_Y | Primitivas; separación insuficiente |
| Carro Y y apoyos de X | Y_CARRIAGE | Carro paramétrico |
| Superficie del módulo X | X_MODULE, hijo de Y_CARRIAGE | Región piloto transportada por Y |
| Servo X, tapa y marca de eje | X_MODULE | Primitivas; no siguen al carro X |
| Carro X y módulo/servo Z | X_CARRIAGE y Z_MODULE | Primitivas; mezcla con cables y guías |
| Carro Z y herramienta | Z_CARRIAGE y TOOL | Primitivas; conjunto neumático fusionado |
| Cables largos y objetos apoyados en la mesa | Sólo referencia | Excluir de la selección piloto |
| Nube de puntos | Referencia independiente | No registrar ni mezclar con la Mesh |

La clasificación combina fotos, continuidad y jerarquía validada. Una región negra puede contener piezas con movimientos diferentes; no se asignan links sólo por color. No se identificó una pared que aporte geometría útil; los extremos globales incluyen también restos al nivel del piso, que quedan fuera del piloto.

## Escala y orientación frente al robot real

Se conserva **escala uniforme 1.0**, coherente con las unidades 3DM. La superficie superior candidata está aproximadamente a 0.858 m, compatible con mesa de 0.85 m más goma de 0.01 m. Su ajuste de plano presenta una desviación RMS aproximada de 1.45 mm y normal casi vertical, lo que respalda Z arriba sin demostrar un registro global en XY.

La región superior candidata tiene bounding box aproximado **0.6088 × 0.9039 × 0.0179 m** en los ejes del archivo: dimensión corta en X y larga en Y, al revés de X 0.90 e Y 0.60 del modelo validado. Los candidatos de alineación por mesa requieren aproximadamente -87° o +93° sobre Z. No se elige esa rotación global porque no establece una correspondencia inequívoca con los módulos y fotografías.

En una región semejante a la viga X se detectaron dos superficies longitudinales. Una rotación cercana a **+2.58° sobre Z** alinea su dirección con X. La separación de planos sugiere aproximadamente 0.038 m y la extensión vertical alrededor de 0.11 m, diferentes de profundidad 0.110 m y altura 0.055 m suministradas. Pueden ser subconjuntos, superficies fusionadas o una orientación distinta: no prueban que se recuperó el módulo completo ni justifican escalar cada eje por separado.

Por eso se registra sólo una región con escala 1, rotación Z 0.0450294947 rad y traslación [0.16, -0.34982, 0.0365] m. Se selecciona una superficie dentro de la envolvente conservadora de X y se exporta respecto al origen de X_MODULE. Es un registro local de piloto, no la posición global de toda la máquina, el estado de los joints durante el scan ni un homing.

## Alcance y datos pendientes

Se aplica la alternativa del punto 36: preparar, limpiar, exportar e integrar una pieza controlada y validar todo el pipeline. Las partes que mezclan cuerpos móviles o presentan orientación ambigua mantienen primitivas. Los recorridos siguen provisionales y no se deducen de las capturas.

Para ampliar el piloto conviene medir correspondencia X/Y de la mesa, sección real de X y altura de su guía, puntos de registro comunes entre scan y montaje, tamaños de carros, offsets de módulos/TCP y una posición conocida de los ejes durante otra captura. Capturas por link o con mayor separación ayudarían a segmentar. Procedimiento y conteos: docs/mesh_integration.md y docs/mesh_processing.json.

Referencia del lector: [API oficial File3dm de rhino3dm](https://mcneel.github.io/rhino3dm/python/api/File3dm.html).
