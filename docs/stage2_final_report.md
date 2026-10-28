# Reporte final de etapa 2

Resultado: piloto visual controlado completado según el criterio 36. Se integró una superficie parcial escaneada de X y se validó el pipeline completo, conservando la cinemática de la etapa 1. La calidad del scan no permite una sustitución fiable de todos los links.

1. **Trabajo realizado.** Inspección de ambos 3DM y sus texturas; conversión no destructiva; escenas de Blender; registro rígido de una región; selección, limpieza, reducción y exportación OBJ; integración visual en Webots; pruebas estáticas y dinámicas; documentación reproducible.

2. **Git inicial.** No había repositorio Git inicializado. No se creó repositorio ni commit. Se guardó un checkpoint de 33 archivos con hashes en [backups/stage1_validated](E:/ROBOTICA/CARTESIANO/backups/stage1_validated/checkpoint_manifest.json).

3. **Archivos creados/modificados.** El listado íntegro, con tamaño y SHA256, está en [stage2_change_manifest.json](E:/ROBOTICA/CARTESIANO/docs/stage2_change_manifest.json). Incluye scripts de inspección/Blender, configuración visual, OBJ/textura, escenas, PROTO, mundo principal y mundo auxiliar, validador complementario, documentos, vistas y evidencias. El controlador principal, runtime.ini y robot_parameters.json permanecen byte por byte iguales al checkpoint.

4. **Cada 3DM.** `untitled 2.3dm`: 7.463.644 bytes, archivo 3DM versión 80. `untitled.3dm`: 7.463.712 bytes, versión 90. Cada uno contiene una Mesh de 16.217 vértices, 24.851 polígonos originales/25.000 triángulos y una PointCloud de 2.775 puntos; un material y atlas PNG RGBA 2048×2048 embebido. Geometría y UV idénticas entre archivos. Bbox de Mesh: mínimo (-0.555205, -0.795830, -0.006297), máximo (0.398178, 0.871380, 1.658526) m; dimensiones 0.953383×1.667210×1.664823 m. Análisis completo: [scan_analysis.md](E:/ROBOTICA/CARTESIANO/docs/scan_analysis.md).

5. **Escala.** Unidades declaradas: metros. Escala uniforme 1, comprobada contra altura y dimensiones de mesa/módulos identificados. No hubo deformación independiente de X/Y/Z.

6. **Orientación.** +Z del scan es arriba; el módulo X tiene aproximadamente 2.58° de yaw respecto a X. Para el piloto se aplicó Rz(+0.045029495 rad) y traslación (0.16, -0.34982, 0.0365) m. Es un registro local de esa región, no un alineamiento global ni una posición home real. OBJ Y-forward/Z-up se verificó como conversión identidad al ENU actual.

7. **Objetos/links identificados.** Mesa, gabinete, soportes, Y fijo, carro Y, módulo X/servo X, carro X, módulo Z/servo Z, carro Z, herramienta y portacables. Las piezas están fusionadas en la captura; los componentes topológicos no equivalen a links cinemáticos. La mesa/gabinete/Y fijo pertenecen a base; el módulo X al conjunto Y; Z al carro X; la herramienta al carro Z. No se clasificó sólo por color.

8. **Meshes creadas.** Derivado completo `blender/derived/scan_raw.obj` para análisis y una Mesh operativa [axis_x_surface_visual.obj](E:/ROBOTICA/CARTESIANO/meshes/axis_x_surface_visual.obj). No se exportaron ficticiamente todas las piezas de la captura.

9. **Polígonos antes/después.** Selección: 359 triángulos. Limpieza: 346 triángulos/298 vértices, eliminando 13 caras de seis islas pequeñas mediante conectividad virtual a 1 µm, sin soldar UV. Decimate: 300 triángulos/274 vértices; reducción 13.29% por Decimate, 16.43% total respecto a la selección. Bbox final 0.810780×0.112414×0.059659 m. [mesh_processing.json](E:/ROBOTICA/CARTESIANO/docs/mesh_processing.json).

10. **Parte que usa Mesh.** Superficie parcial del módulo X bajo `X_MODULE`, hijo de `Y_CARRIAGE`. Viaja con Y y permanece en la guía cuando se deslizan los carros X y Z. Origen igual al Solid; escala local 1 y rotación cero. Se retiraron sólo los visuales anteriores del cuerpo y guía superior de X.

11. **Primitivas conservadas.** Mesa, gabinete, Y/Z, todos los carros, herramienta, servos, tapa y marcador X. Un núcleo visual interior de X de 0.805×0.025×0.040 m cubre huecos del scan parcial. Todos los boundingObjects, Physics, ejes, joints y jerarquía original se conservaron; ningún scan se usa para colisión.

12. **Webots.** R2025a cargó OBJ, UV y textura usando rutas relativas y PBRAppearance. Las ejecuciones finales terminaron con código 0, sin errores, warnings ni errores OpenGL en los logs. El mundo final también se inició con el controlador original en demo continua; [stage2_demo_evidence.json](E:/ROBOTICA/CARTESIANO/docs/stage2_demo_evidence.json) registra el proceso y el controlador.

13. **Validaciones.** Guard estático 14/14; pruebas originales 23/23; prueba auxiliar 34/34, que incluye las 23 originales y 11 comprobaciones de recurso, nueve posiciones negativa/centro/positiva de Y/X/Z y captura cercana. Error máximo de seguimiento de Mesh: 0.000000968 m. [validation_report.json](E:/ROBOTICA/CARTESIANO/docs/validation_report.json), [scan_visual_validation.json](E:/ROBOTICA/CARTESIANO/docs/scan_visual_validation.json).

14. **Regresiones.** Ninguna detectada. Las cinco métricas continuas y los 193.424 s simulados de la prueba original son idénticos al checkpoint: error máximo TCP 0.202497 mm, deriva fija 0, excursión máxima de sensor 0.049050 mm, diferencia de orientación 1.92614e-5, separación mínima herramienta/goma 0.209749 m. Permanecen exactamente tres SliderJoint, tres LinearMotor y tres PositionSensor. Las 13 referencias originales conservaron sus hashes. [stage2_regression_comparison.json](E:/ROBOTICA/CARTESIANO/docs/stage2_regression_comparison.json).

15. **Tamaño/rendimiento.** OBJ final 32.157 bytes; JPEG 854.785 bytes; total visual 886.942 bytes. Blend final 1.860.494 bytes. Arranque hasta primer paso ≈2.67 s; prueba auxiliar total ≈52.92 s para 258.32 s simulados (≈4.88× incluyendo capturas). FPS y tiempo aislado de carga no instrumentados. [scan_performance.json](E:/ROBOTICA/CARTESIANO/docs/scan_performance.json).

16. **Problemas.** Archivos duplicados geométricamente; máquina fusionada; gabinete deformado; tabla con dimensión larga en Y del scan frente a X del modelo; discrepancia de sección aparente de X; superficies rugosas y parciales; nube con registro XY distinto. La primera prueba auxiliar falló al leer `scale` de un Transform que Webots expuso como Pose. Se corrigió el comprobador y repitió exitosamente; el informe fallido y su explicación se preservan en docs. No fue un cambio de física ni de controlador principal.

17. **Decisiones Blender.** Blender 5.2.2 LTS en background con factory-startup, sin modificar la sesión GUI del usuario. rhino3dm 8.35.0 instalado sólo en `.tools/scan_reader` con Python 3.12 bundled; Webots conserva Python 3.14.4. Se preservaron UV, exportaron normales calculadas por Blender, aplicaron transformaciones a coordenadas exportadas, eligió origen del link, descartaron ruido y regiones ambiguas y evitó cerrar/deformar artificialmente la superficie escaneada. Pipeline y comandos: [mesh_integration.md](E:/ROBOTICA/CARTESIANO/docs/mesh_integration.md).

18. **Blend.** [E:\ROBOTICA\CARTESIANO\blender\cartesian_scan_cleanup.blend](E:/ROBOTICA/CARTESIANO/blender/cartesian_scan_cleanup.blend). Incluye referencias cruda/alineada ocultas y piloto visible con origen del link.

19. **World.** [E:\ROBOTICA\CARTESIANO\worlds\cartesian_robot.wbt](E:/ROBOTICA/CARTESIANO/worlds/cartesian_robot.wbt). Se abre también mediante tools/open_webots.ps1. Mundo auxiliar: worlds/cartesian_mesh_validation.wbt.

20. **Próximas medidas.** Sección real y caras de referencia de X; correspondencia de los ejes de mesa; puntos comunes de registro; centros/orígenes y offsets de carros, servos y módulos; TCP; homing y recorridos reales. Conviene escanear cada link por separado con una posición de montaje conocida antes de ampliar esta integración. Los límites actuales continúan provisionales.

21. **Capturas.** [Vista final Webots](E:/ROBOTICA/CARTESIANO/docs/validation.jpg), [detalle del piloto](E:/ROBOTICA/CARTESIANO/docs/scan_views/webots_mesh_closeup.jpg) y nueve capturas de extremos/centro en docs/scan_views/webots_*.jpg. También se conservan cuatro vistas crudas y cuatro procesadas de Blender.
