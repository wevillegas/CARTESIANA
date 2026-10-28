# Mesh visual del piloto

`axis_x_surface_visual.obj` es una superficie parcial escaneada del módulo X, preparada con Blender 5.2.2 LTS desde un derivado de `referencias/untitled 2.3dm`. Los originales permanecen intactos.

El OBJ tiene **300 triángulos, 274 vértices y 32 157 bytes**; conserva UV y contiene normales calculadas por Blender. Usa el atlas derivado `../textures/scan_atlas.jpg`. Sus coordenadas están en metros, locales al Solid `X_MODULE`, con escala 1 y rotación local cero. Viaja con Y; el desplazamiento relativo del carro X no mueve la guía.

Esta Mesh se utiliza sólo como geometría visual. Los `boundingObject` mantienen las primitivas Box/Cylinder de la etapa 1. Un pequeño núcleo visual paramétrico completa huecos de la superficie; las otras piezas continúan usando primitivas.

Procedimiento, origen, limpieza y validación: `../docs/mesh_integration.md`. Análisis y límites de la captura: `../docs/scan_analysis.md`. Conteos reproducibles: `../docs/mesh_processing.json`.
