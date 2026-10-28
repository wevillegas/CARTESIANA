"""Regenera modelo SI y visuales opcionales del scan, sin cambiar la cinemática."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / 'config' / 'robot_parameters.json').read_text(encoding='utf-8'))
D = P['measured_dimensions']
A = P['approximate_dimensions']
POS = P['placements']
SCAN_CONFIG_PATH = ROOT / 'config' / 'scan_integration.json'
SCAN = json.loads(SCAN_CONFIG_PATH.read_text(encoding='utf-8')) if SCAN_CONFIG_PATH.exists() else {}
CAD_CONFIG_PATH = ROOT / 'config' / 'cad_integration.json'
CAD = json.loads(CAD_CONFIG_PATH.read_text(encoding='utf-8')) if CAD_CONFIG_PATH.exists() else {}


def vec(values):
    return ' '.join(f'{v:.6g}' for v in values)


COLORS = {
    'frame': ('0.68 0.70 0.67', 0.35, 0.7),
    'metal': ('0.72 0.75 0.78', 0.8, 0.35),
    'rail': ('0.40 0.43 0.47', 0.8, 0.3),
    'black': ('0.035 0.04 0.045', 0.1, 0.65),
    'rubber': ('0.065 0.065 0.06', 0, 0.95),
    'cabinet': ('0.82 0.83 0.80', 0.15, 0.7),
    'red': ('0.7 0.05 0.03', 0.1, 0.6),
    'x': ('0.85 0.12 0.08', 0, 0.6),
    'y': ('0.1 0.65 0.22', 0, 0.6),
    'z': ('0.12 0.38 0.92', 0, 0.6),
    'switch': ('0.95 0.78 0.05', 0, 0.5),
}


def shape(geometry, color):
    rgb, metal, rough = COLORS[color]
    return f'Shape {{ appearance PBRAppearance {{ baseColor {rgb} metalness {metal} roughness {rough} }} geometry {geometry} }}'


def box(position, size, color='metal', collision=False):
    geometry = f'Box {{ size {vec(size)} }}'
    child = geometry if collision else shape(geometry, color)
    return f'Transform {{ translation {vec(position)} children [ {child} ] }}'


def cylinder(position, radius, height, color='metal', collision=False, rotation=None):
    geometry = f'Cylinder {{ radius {radius} height {height} subdivision 20 }}'
    child = geometry if collision else shape(geometry, color)
    rotate = f'rotation {vec(rotation)}' if rotation else ''
    return f'Transform {{ translation {vec(position)} {rotate} children [ {child} ] }}'


def group(children):
    return 'Group { children [\n' + '\n'.join(children) + '\n] }'


def solid(defname, name, position, children, bounds=None, mass=None, rotation=None):
    # Sólo sustituir visuales. No tocar Solids descendientes, joints ni boundingObject.
    for part in CAD.get('parts', []):
        if not part.get('enabled') or part['solid_def'] != defname:
            continue
        if part['confidence_class'] not in ('A', 'B'):
            raise ValueError('Only verified CAD classes A/B can be integrated automatically')
        removed = set(part['remove_visual_indices'])
        if any(index < 0 or index >= len(children) or not children[index].startswith('Transform {') for index in removed):
            raise ValueError(f'{defname}: CAD may replace only known primitive visual branches')
        children = [child for index, child in enumerate(children) if index not in removed]
        cad_shapes = []
        for mesh in part['meshes']:
            path = Path(mesh['path'])
            if path.is_absolute() or '..' in path.parts or not (ROOT / path).is_file():
                raise ValueError(f'Invalid local CAD mesh: {path}')
            rgb = vec(mesh['rgb'])
            metalness = .65 if mesh['rgb'][0] > .6 else .15
            cad_shapes.append(f'Shape {{ appearance PBRAppearance {{ baseColor {rgb} metalness {metalness} roughness 0.4 }} geometry Mesh {{ url [ "../{path.as_posix()}" ] }} }}')
        # Mesh coordinates are already relative to this unchanged Solid; no offsets or scaling nodes.
        children.append(f'DEF {part["visual_def"]} Transform {{ children [ ' + '\n'.join(cad_shapes) + ' ] }')
    for part in SCAN.get('parts', []):
        if part.get('enabled', True) and part['solid_def'] == defname:
            removed = set(part.get('remove_visual_indices', []))
            if any(index < 0 or index >= len(children) or not children[index].startswith('Transform {') for index in removed):
                raise ValueError(f'{defname}: sólo se pueden sustituir ramas Transform visuales conocidas')
            children = [child for index, child in enumerate(children) if index not in removed]
            backing = part.get('primitive_backing')
            if backing:
                children.append(box(backing['position'], backing['size'], backing.get('color', 'metal')))
            asset = ROOT / 'meshes' / (part['name'] + '.obj')
            texture = ROOT / SCAN['texture']
            if not asset.is_file() or not texture.is_file():
                raise FileNotFoundError('Preparar/exportar la mesh y textura antes de generar el modelo')
            # OBJ ya está en metros ENU y relativo al origen del Solid: transformación identidad.
            children.append(f'''DEF SCAN_X_VISUAL Transform {{
              children [ Shape {{
                appearance PBRAppearance {{ baseColor 1 1 1 metalness 0 roughness 0.85
                  baseColorMap ImageTexture {{ url [ "../{SCAN['texture']}" ] }} }}
                geometry Mesh {{ url [ "../meshes/{part['name']}.obj" ] }}
              }} ]
            }}''')
    bo = f'boundingObject {group(bounds)}' if bounds else ''
    physics = f'physics Physics {{ density -1 mass {mass} }}' if mass else ''
    rot = f' rotation {vec(rotation)}' if rotation else ''
    return f'DEF {defname} Solid {{ translation {vec(position)}{rot} name "{name}" children [\n' + '\n'.join(children) + f'\n] {bo} {physics} }}'


def joint(axis, endpoint):
    limits = P['limits'][axis]
    # Hard stops quedan fuera de los límites de mando, para no arrancar contra un tope.
    stop_margin = 0.005
    ax = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
    return f'''DEF JOINT_{axis.upper()} SliderJoint {{
      jointParameters JointParameters {{
        axis {vec(ax)} position 0
        minStop {limits['min'] - stop_margin:.6g} maxStop {limits['max'] + stop_margin:.6g}
        dampingConstant 2
      }}
      device [
        LinearMotor {{ name "motor_{axis}" minPosition {limits['min']} maxPosition {limits['max']}
          maxVelocity {P['speeds'][axis]} acceleration {P['acceleration']}
          maxForce {P['simulation_max_force_N'][axis]} controlPID {P['control_gain']} 0 0 sound "" }}
        PositionSensor {{ name "sensor_{axis}" }}
      ]
      endPoint {endpoint}
    }}'''


def finger(side):
    """Dedo de la pinza: SliderJoint propio, abre en 0 y cierra hacia el centro."""
    G = P['gripper']
    sign = -1 if side == 'left' else 1
    ax = [-sign, 0, 0]  # cerrar = moverse hacia el eje de la herramienta
    size = G['finger_size']
    pos = [sign * G['finger_open_x'], 0, POS['tool_in_z'][2] + G['finger_center_z_in_tool']]
    color = 'red'
    body = box([0, 0, 0], size, color)
    pad = box([-sign * (size[0] / 2 + .001), 0, -size[2] / 4], [.002, size[1], size[2] / 2], 'black')
    end = (f'Solid {{ translation {vec(pos)} name "dedo_{side}" children [ {body} {pad} ] '
           f'boundingObject {box([0, 0, 0], size, collision=True)} '
           f'physics Physics {{ density -1 mass {G["finger_mass_kg"]} }} }}')
    return f'''SliderJoint {{
      jointParameters JointParameters {{ axis {vec(ax)} position 0 minStop -0.001 maxStop {G['travel'] + 0.001:.6g} dampingConstant 1 }}
      device [
        LinearMotor {{ name "grip_{side}" minPosition 0 maxPosition {G['travel']} maxVelocity {G['max_velocity']} maxForce {G['max_force']} sound "" }}
        PositionSensor {{ name "grip_{side}_sensor" }}
      ]
      endPoint {end}
    }}'''


def tool_tip_world(axis_xy, z):
    """Punta de la herramienta (ENU) para desplazamientos de eje (x, y, z)."""
    t = P['tool_tip_zero']
    return [t[0] + axis_xy[0], t[1] + axis_xy[1], t[2] + z]


def machine_to_joint(axis, value_mm):
    """Coordenada de máquina (mm, cero en el sensor de inicio de carrera) -> articulación (m)."""
    H = P['homing']
    low, high = P['limits'][axis]['min'], P['limits'][axis]['max']
    switch = low + H['switch_tolerance'] if H['switch_at'][axis] == 'min' else high - H['switch_tolerance']
    return switch + value_mm / 1000.0


def workcell_nodes():
    """Zócalos sobre columnas y pieza, ubicados donde la pinza los alcanza."""
    W, G = P['workcell'], P['gripper']
    surface = P['table_surface_z']
    plate = W['socket_plate']
    nodes = []
    pick_z = machine_to_joint('z', W['pick_z_mm'])
    sockets = {n: [machine_to_joint('x', v[0]), machine_to_joint('y', v[1])] for n, v in W['sockets_mm'].items()}
    for name, xy in sockets.items():
        tip = tool_tip_world(xy, pick_z)
        # Base de la pieza = centro de agarre - medio lado; la placa queda justo debajo.
        top = tip[2] - G['grip_center_below_tip'] - G['piece_size'] / 2
        col_h = top - plate[2] - surface
        if col_h <= 0.02:
            raise ValueError(f'Zócalo {name}: columna demasiado baja ({col_h:.3f} m)')
        px, py = W['pedestal_size_xy']
        col = shape(f'Box {{ size {px} {py} {col_h:.6g} }}', 'frame')
        plt = shape(f'Box {{ size {vec(plate)} }}', 'y' if name == 'A' else 'z')
        nodes.append(
            f'DEF ZOCALO_{name} Solid {{ translation {tip[0]:.6g} {tip[1]:.6g} {surface:.6g} name "zocalo_{name}" children [\n'
            f'  Transform {{ translation 0 0 {col_h / 2:.6g} children [ {col} ] }}\n'
            f'  Transform {{ translation 0 0 {col_h + plate[2] / 2:.6g} children [ {plt} ] }}\n'
            f'] boundingObject Group {{ children [ Transform {{ translation 0 0 {col_h / 2:.6g} children [ Box {{ size {px} {py} {col_h:.6g} }} ] }} '
            f'Transform {{ translation 0 0 {col_h + plate[2] / 2:.6g} children [ Box {{ size {vec(plate)} }} ] }} ] }} }}')
    start = sockets[W['piece_start']]
    tip = tool_tip_world(start, pick_z)
    c = [tip[0], tip[1], tip[2] - G['grip_center_below_tip']]
    s = G['piece_size']
    # Sin Physics ni boundingObject: el controlador (Supervisor) la traslada al agarrarla.
    nodes.append(f'DEF PIEZA Solid {{ translation {vec(c)} name "pieza" children [ '
                 f'{shape(f"Box {{ size {s} {s} {s} }}", "x")} ] }}')
    return nodes


def check_parameters():
    for axis, dim, carriage, index in [('x', 'x_module', 'x_carriage', 0), ('y', 'y_module', 'y_carriage', 1), ('z', 'z_module', 'z_carriage', 2)]:
        limits = P['limits'][axis]
        if not all(math.isfinite(v) for v in limits.values()) or not limits['min'] < 0 < limits['max']:
            raise ValueError(f'Limites {axis}: deben ser finitos e incluir el cero inicial en su interior')
        module_center = {'x': 0, 'y': 0, 'z': POS['y_carriage'][2] + POS['x_carriage_in_y'][2] + POS['z_module_in_x'][2]}[axis]
        carriage_center = {'x': 0, 'y': 0, 'z': POS['y_carriage'][2] + POS['x_carriage_in_y'][2] + POS['z_carriage_in_x'][2]}[axis]
        half_available = D[dim][index] / 2 - A[carriage][index] / 2 - P['geometry_margin_m']
        for target in limits.values():
            if abs(carriage_center + target - module_center) + 0.005 > half_available:
                raise ValueError(f'Limite {axis}={target} incompatible con guía, carro y margen')
    tip = [POS['y_carriage'][i] + POS['x_carriage_in_y'][i] + POS['z_carriage_in_x'][i] + POS['tool_tip_in_z'][i] for i in range(3)]
    if any(abs(a-b) > 1e-9 for a, b in zip(tip, P['tool_tip_zero'])):
        raise ValueError('tool_tip_zero no coincide con el montaje')
    if tip[2] + P['limits']['z']['min'] <= P['table_surface_z'] + .02:
        raise ValueError('La herramienta invade la mesa')


def viewpoint(eye, target):
    """Orientación axis-angle de un Viewpoint R2025a (mira por +X local, FLU) hacia target."""
    forward=[target[i]-eye[i] for i in range(3)]
    length=math.sqrt(sum(v*v for v in forward)); forward=[v/length for v in forward]
    right=[forward[1],-forward[0],0]
    length=math.sqrt(sum(v*v for v in right)); right=[v/length for v in right]
    up=[right[1]*forward[2]-right[2]*forward[1], right[2]*forward[0]-right[0]*forward[2],right[0]*forward[1]-right[1]*forward[0]]
    matrix=[[forward[i],-right[i],up[i]] for i in range(3)]
    angle=math.acos((sum(matrix[i][i] for i in range(3))-1)/2)
    axis=[matrix[2][1]-matrix[1][2],matrix[0][2]-matrix[2][0],matrix[1][0]-matrix[0][1]]
    length=math.sqrt(sum(v*v for v in axis)); axis=[v/length for v in axis]
    return axis, angle, eye


def build():
    check_parameters()
    fixed_visual, fixed_bounds = [], []
    # Altura del bastidor 0.85 m; goma agregada arriba: superficie final 0.86 m.
    table_x, table_y, table_h = D['table']
    bar = D['main_bar_width']
    for x in [-table_x/2 + bar/2, table_x/2 - bar/2]:
        for y in [-table_y/2 + D['side_bar_width']/2, table_y/2 - D['side_bar_width']/2]:
            position, size = [x, y, (table_h-bar)/2], [bar, D['side_bar_width'], table_h-bar]
            fixed_visual.append(box(position, size, 'frame'))
            fixed_bounds.append(box(position, size, collision=True))
    for z in [table_h - bar/2, D['lower_crossbar_height']]:
        for y in [-table_y/2 + bar/2, table_y/2-bar/2]:
            fixed_visual.append(box([0, y, z], [table_x, bar, bar], 'frame'))
            fixed_bounds.append(box([0, y, z], [table_x, bar, bar], collision=True))
        for x in [-table_x/2 + D['side_bar_width']/2, table_x/2-D['side_bar_width']/2]:
            fixed_visual.append(box([x, 0, z], [D['side_bar_width'], table_y, bar], 'frame'))
            fixed_bounds.append(box([x, 0, z], [D['side_bar_width'], table_y, bar], collision=True))
    top_pos = [0, 0, table_h + D['rubber_thickness']/2]
    top_size = [table_x, table_y, D['rubber_thickness']]
    fixed_visual.append(box(top_pos, top_size, 'rubber'))
    fixed_bounds.append(box(top_pos, top_size, collision=True))
    # Tablero simplificado, cerrado, al lado derecho (+X) de la mesa con la puerta hacia afuera.
    fixed_visual.append(solid('CABINET', 'gabinete_electrico', POS['cabinet'], [
        box([0,0,0], D['cabinet'], 'cabinet'),
        box([0,-D['cabinet'][1]/2-.008,0], [D['cabinet'][0],.016,D['cabinet'][2]], 'cabinet'),
        box([.245,-.184,0], [.016,.016,.08], 'black')
    ], [box([0,-.008,0], [D['cabinet'][0],D['cabinet_with_cover_depth'],D['cabinet'][2]], collision=True),
        box([.245,-.184,0],[.016,.016,.08],collision=True)], rotation=POS.get('cabinet_rotation')))
    for y in [-.22,.22]:
        pos=[POS['fixed_y'][0],y,P['table_surface_z']+D['support'][2]/2]
        fixed_visual.append(box(pos,D['support'],'frame'))
        fixed_bounds.append(box(pos,D['support'],collision=True))
    fixed_visual.append(solid('FIXED_Y','modulo_y_fijo',POS['fixed_y'],[
        box([0,0,0],D['y_module']),
        box([0,0,.048],[.025,.67,.006],'rail'),
        box([0,D['y_module'][1]/2 + D['y_servo'][1]/2,0],D['y_servo'],'black'),
        box([0,-.346,0],[.057,.018,.098],'black'),
        # Sensor de inicio de carrera Y (visual): donde llega el carro en Y mínimo.
        box([.028,P['limits']['y']['min']-A['y_carriage'][1]/2-.008,.03],[.014,.012,.02],'switch')
    ], [box([0,0,0],D['y_module'],collision=True),box([0,D['y_module'][1]/2+D['y_servo'][1]/2,0],D['y_servo'],collision=True)]))
    # Z móvil, con herramienta rigidamente unida y punto de referencia independiente.
    tool = solid('TOOL','herramienta_neumatica_aproximada',POS['tool_in_z'],[
        box([0,0,.03], A['tool_body']),
        cylinder([0,0,-.02], A['tool_shaft_radius'], A['tool_shaft_length']),
        box([0,0,-.071],[.07,.024,.008],'black')
    ])
    zparts=[box([0,0,0],A['z_carriage']), box([0,-.022,0],[.08,.01,.07],'black'),
            cylinder([-.028,0,-.065],.006,.10), cylinder([.028,0,-.065],.006,.10), tool,
            # Dedos colgados del carro Z (que tiene Physics), no de TOOL: un joint con
            # endPoint físico necesita un padre físico para viajar con el carro.
            finger('left'), finger('right'),
            solid('TOOL_TIP','punto_herramienta',POS['tool_tip_in_z'],[])]
    zsolid=solid('Z_CARRIAGE','carro_z_y_herramienta',POS['z_carriage_in_x'],zparts,[
        box([0,0,0],A['z_carriage'],collision=True),
        box([0,0,-.13],A['tool_body'],collision=True),
        cylinder([0,0,-.18],A['tool_shaft_radius'],A['tool_shaft_length'],collision=True),
        box([0,0,-.231],[.07,.024,.008],collision=True)
    ],P['approximate_mass_kg']['z_assembly'])
    zcenter=POS['z_module_in_x']
    zmodule=solid('Z_MODULE','modulo_z_y_servo',zcenter,[
        box([0,0,0],D['z_module']),
        box([0,-.049,0],[.024,.006,.335],'rail'),
        box([0,0,D['z_module'][2]/2 + D['z_servo'][2]/2],D['z_servo'],'black'),
        box([0,-.04,.112],[.042,.015,.03],'z'),
        # Sensor de inicio de carrera Z (visual): arriba, donde llega el carro en Z máximo.
        box([0,-.052,POS['z_carriage_in_x'][2]+P['limits']['z']['max']+A['z_carriage'][2]/2+.008-zcenter[2]],[.012,.012,.012],'switch')
    ])
    xparts=[box([0,0,0],A['x_carriage']),box([0,0,-.021],[.10,.065,.007],'rail'),
            box([0,-.055,.025],[.10,.05,.07],'black'),zmodule,joint('z',zsolid)]
    xsolid=solid('X_CARRIAGE','carro_x_con_eje_z',POS['x_carriage_in_y'],xparts,[
        box([0,0,0],A['x_carriage'],collision=True),
        box(zcenter,D['z_module'],collision=True),
        box([zcenter[0],zcenter[1],zcenter[2]+D['z_module'][2]/2+D['z_servo'][2]/2],D['z_servo'],collision=True)
    ],P['approximate_mass_kg']['x_assembly'])
    xcenter=POS['x_module_in_y']
    xmodule=solid('X_MODULE','modulo_x_y_servo',xcenter,[
        box([0,0,0],D['x_module']),
        box([0,0,.030],[.78,.05,.005],'rail'),
        box([D['x_module'][0]/2 + D['x_servo'][0]/2,0,0],D['x_servo'],'black'),
        box([-.398,0,0],[.019,.118,.062],'black'),
        box([.37,-.058,0],[.032,.01,.03],'x'),
        # Sensor de inicio de carrera X (visual): donde llega el carro en X mínimo.
        box([P['limits']['x']['min']-A['x_carriage'][0]/2-.008,-.062,.02],[.012,.012,.02],'switch')
    ])
    yparts=[box([0,0,0],A['y_carriage']),xmodule,joint('x',xsolid)]
    # Portacables: segmentos simplificados rígidos decorativos, no cadena flexible física.
    for i in range(16):
        yparts.append(box([.04+i*.043,.072,.085],[.035,.027,.018],'black'))
    yparts.append(box([0,-.085,.005],[.028,.01,.022],'y'))
    ysolid=solid('Y_CARRIAGE','carro_y_con_eje_x',POS['y_carriage'],yparts,[
        box([0,0,0],A['y_carriage'],collision=True),
        box(xcenter,D['x_module'],collision=True),
        box([xcenter[0]+D['x_module'][0]/2+D['x_servo'][0]/2,0,xcenter[2]],D['x_servo'],collision=True)
    ],P['approximate_mass_kg']['y_assembly'])
    fixed_visual.append(joint('y',ysolid))
    proto='''#VRML_SIM R2025a utf8
# Modelo generado por tools/build_model.py; parámetros SI y visuales en config/.
# Recorridos, carros, posiciones de montaje, masas y fuerzas son aproximados.
PROTO CartesianRobot [
  field SFVec3f translation 0 0 0
  field SFRotation rotation 0 0 1 0
  field SFString name "cartesian_robot"
  field SFString controller "cartesian_controller"
] {
  Robot {
    translation IS translation
    rotation IS rotation
    name IS name
    controller IS controller
    supervisor TRUE
    selfCollision FALSE
    children [
'''+ '\n'.join(fixed_visual) + '\n] boundingObject ' + group(fixed_bounds) + '\n}\n}\n'
    (ROOT/'protos'/'CartesianRobot.proto').write_text(proto,encoding='utf-8')
    # Cámara calculada: +X aparece hacia la derecha, +Y hacia el fondo.
    axis, angle, eye = viewpoint([2.6,-3.8,2.6], [0,-.03,.91])
    world_title = ('Robot cartesiano industrial XYZ - etapa 2B CAD' if any(p.get('enabled') for p in CAD.get('parts', []))
                   else 'Robot cartesiano industrial XYZ - etapa 2 (piloto visual)' if SCAN else 'Robot cartesiano industrial XYZ - etapa 1')
    world=f'''#VRML_SIM R2025a utf8
EXTERNPROTO "../protos/CartesianRobot.proto"
WorldInfo {{ title "{world_title}" basicTimeStep 16 coordinateSystem "ENU" randomSeed 1 }}
Viewpoint {{ orientation {vec(axis+[angle])} position {vec(eye)} fieldOfView 0.9 near 0.05 }}
Background {{ skyColor [ 0.16 0.20 0.25 ] }}
DirectionalLight {{ direction -0.4 0.6 -1 intensity 1 ambientIntensity 0.6 }}
DirectionalLight {{ direction 0.6 -0.4 -0.7 intensity 1 }}
Solid {{ translation 0 0 -0.015 name "piso" children [ {shape('Box { size 5 5 0.03 }','frame')} ] boundingObject Box {{ size 5 5 0.03 }} }}
DEF CARTESIAN_ROBOT CartesianRobot {{ }}
'''
    (ROOT/'worlds'/'cartesian_robot.wbt').write_text(world,encoding='utf-8')
    if 'workcell' in P:
        tcp_world = world.replace(f'title "{world_title}"', 'title "CARTESIANA - gemelo digital con conexion TCP/IP"')
        cam_axis, cam_angle, cam_eye = viewpoint([1.15, -1.75, 1.65], [0.0, -0.12, 1.08])
        tcp_world = tcp_world.replace(f'Viewpoint {{ orientation {vec(axis+[angle])} position {vec(eye)}',
                                      f'Viewpoint {{ orientation {vec(cam_axis+[cam_angle])} position {vec(cam_eye)}')
        tcp_world = tcp_world.replace('DEF CARTESIAN_ROBOT CartesianRobot { }',
                                      'DEF CARTESIAN_ROBOT CartesianRobot { controller "cartesiana_tcp" }\n' + '\n'.join(workcell_nodes()))
        (ROOT/'worlds'/'cartesiana_tcp.wbt').write_text(tcp_world,encoding='utf-8')
    if SCAN:
        visual_test_world = world.replace('DEF CARTESIAN_ROBOT CartesianRobot { }',
                                         'DEF CARTESIAN_ROBOT CartesianRobot { controller "mesh_visual_validation" }')
        (ROOT/'worlds'/'cartesian_mesh_validation.wbt').write_text(visual_test_world,encoding='utf-8')
    if CAD:
        cad_test_world = world.replace('DEF CARTESIAN_ROBOT CartesianRobot { }',
                                      'DEF CARTESIAN_ROBOT CartesianRobot { controller "cad_visual_validation" }')
        (ROOT/'worlds'/'cartesian_cad_validation.wbt').write_text(cad_test_world,encoding='utf-8')
    print('Generados: protos/CartesianRobot.proto, worlds/cartesian_robot.wbt y worlds/cartesiana_tcp.wbt')


if __name__=='__main__':
    build()
