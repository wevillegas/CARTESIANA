# Análisis de escaneos 3D

Inspección de lectura con rhino3dm 8.35.0. Los archivos originales no se modifican.

La clasificación semántica y la alineación se completarán tras inspeccionar vistas de Blender; no se deducen links sólo del color.

## untitled 2.3dm

- Tamaño: 7,463,644 bytes.
- Formato en disco: archivo 3DM 80; versión normalizada en lector: 80.
- Aplicación: Rhinoceros 9 WIP / iRhino.
- Unidades declaradas: UnitSystem.Meters; escala de unidades a metros: 1.0.
- Objetos: 2; tipos: {'PointCloud': 1, 'Mesh': 1}.
- Materiales: 1; texturas embebidas: 1.
- PointCloud #0: bounding box {'min': [-0.4749314785003662, -0.7972394824028015, 0.8546753525733948], 'max': [0.47394049167633057, 0.2851714789867401, 1.6615071296691895], 'dimensions': [0.9488719701766968, 1.0824109613895416, 0.8068317770957947]}.
- Mesh #1: bounding box {'min': [-0.5552048683166504, -0.7958295941352844, -0.006296967621892691], 'max': [0.3981778025627136, 0.8713800311088562, 1.658525824546814], 'dimensions': [0.953382670879364, 1.6672096252441406, 1.6648227921687067]}.
  - Vértices: 16217; polígonos: 24851; triángulos: 25000; UVs: 16217.
  - Componentes indexados: 200; al unificar coordenadas a 1 micrómetro: 3. Las costuras UV pueden separar índices aunque la superficie sea continua.
  - Cerrada: True; válida: True; aristas de borde: 7034; no manifold: 0; triángulos degenerados: 0.
  - Aristas de borde tras unificar coordenadas sólo para análisis: 0; componentes: [24554, 368, 78].
  - Estos indicadores no demuestran ausencia de agujeros visuales, deformación o fusión de piezas; la inspección visual es obligatoria.

## untitled.3dm

- Tamaño: 7,463,712 bytes.
- Formato en disco: archivo 3DM 90; versión normalizada en lector: 90.
- Aplicación: Rhinoceros 9 WIP / iRhino.
- Unidades declaradas: UnitSystem.Meters; escala de unidades a metros: 1.0.
- Objetos: 2; tipos: {'PointCloud': 1, 'Mesh': 1}.
- Materiales: 1; texturas embebidas: 1.
- PointCloud #0: bounding box {'min': [-0.4749314785003662, -0.7972394824028015, 0.8546753525733948], 'max': [0.47394049167633057, 0.2851714789867401, 1.6615071296691895], 'dimensions': [0.9488719701766968, 1.0824109613895416, 0.8068317770957947]}.
- Mesh #1: bounding box {'min': [-0.5552048683166504, -0.7958295941352844, -0.006296967621892691], 'max': [0.3981778025627136, 0.8713800311088562, 1.658525824546814], 'dimensions': [0.953382670879364, 1.6672096252441406, 1.6648227921687067]}.
  - Vértices: 16217; polígonos: 24851; triángulos: 25000; UVs: 16217.
  - Componentes indexados: 200; al unificar coordenadas a 1 micrómetro: 3. Las costuras UV pueden separar índices aunque la superficie sea continua.
  - Cerrada: True; válida: True; aristas de borde: 7034; no manifold: 0; triángulos degenerados: 0.
  - Aristas de borde tras unificar coordenadas sólo para análisis: 0; componentes: [24554, 368, 78].
  - Estos indicadores no demuestran ausencia de agujeros visuales, deformación o fusión de piezas; la inspección visual es obligatoria.

## Comparación de los dos archivos

La geometría triangular y sus UV son idénticas: True.
No son dos tomas complementarias; no corresponde superponerlas como nuevas observaciones.

## Comparación inicial con medidas

Las unidades son metros. El bounding box global incluye máquina y entorno; no debe forzarse a 0.90 × 0.60 × 0.85 m. La escala se verificará contra la mesa y módulos identificados, con transformaciones rígidas y escala uniforme.

Fuentes de API: [rhino3dm](https://mcneel.github.io/rhino3dm/python/api/File3dm.html).
