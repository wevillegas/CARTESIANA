"""Inspección no destructiva de 3DM y extracción de derivados para Blender.

Ejecutar con Python bundled y rhino3dm instalado sólo en .tools/scan_reader.
Los originales se abren en lectura y sus SHA-256 se verifican antes/después.
"""
from pathlib import Path
import sys
import hashlib
import json
import base64
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools' / 'scan_reader'))
import rhino3dm as rhino


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(points):
    lower, upper = np.min(points, axis=0), np.max(points, axis=0)
    return {'min': lower.tolist(), 'max': upper.tolist(), 'dimensions': (upper-lower).tolist()}


def mesh_arrays(mesh):
    vertices = np.array([(v.X, v.Y, v.Z) for v in mesh.Vertices], dtype=np.float64)
    faces = []
    for a, b, c, d in mesh.Faces:
        faces.append((a,b,c))
        if c != d:
            faces.append((a,c,d))
    uv = np.array([(v.X,v.Y) for v in mesh.TextureCoordinates], dtype=np.float64)
    return vertices, np.asarray(faces, dtype=np.int32), uv


def topology(vertices, faces):
    # Unión por conectividad de vértices; no cambia la malla original.
    parent = list(range(len(vertices)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        a,b = find(a),find(b)
        if a != b:
            parent[b] = a
    edges = Counter()
    degenerate = 0
    for a,b,c in faces:
        union(int(a),int(b)); union(int(b),int(c))
        for u,v in [(a,b),(b,c),(c,a)]:
            edges[tuple(sorted((int(u),int(v))))] += 1
        area2 = np.linalg.norm(np.cross(vertices[b]-vertices[a],vertices[c]-vertices[a]))
        if area2 < 1e-12:
            degenerate += 1
    components = Counter(find(int(f[0])) for f in faces)
    centered = vertices-vertices.mean(axis=0)
    values, vectors = np.linalg.eigh(centered.T@centered/len(vertices))
    return {
        'connected_components':len(components),
        'component_triangle_counts_descending': sorted(components.values(),reverse=True),
        'boundary_edges': sum(n==1 for n in edges.values()),
        'nonmanifold_edges': sum(n>2 for n in edges.values()),
        'degenerate_triangles': degenerate,
        'pca_eigenvalues_descending':values[::-1].tolist(),
        'pca_axes_columns':vectors[:,::-1].tolist(),
        'note':'Los componentes topológicos no equivalen automáticamente a links mecánicos; un scan cerrado puede fusionar piezas.'
    }


def inspect(path):
    before = digest(path)
    model = rhino.File3dm.Read(str(path))
    if model is None:
        raise RuntimeError(f'No se pudo leer {path}')
    info = {
        'file':path.name,'bytes':path.stat().st_size,'sha256':before,
        'archive_version_on_disk':rhino.File3dm.ReadArchiveVersion(str(path)),
        'archive_version_in_reader':model.ArchiveVersion,
        'application_name':model.ApplicationName,'application_details':model.ApplicationDetails,
        'units':str(model.Settings.ModelUnitSystem),
        'declared_scale_to_meters':1.0 if model.Settings.ModelUnitSystem==rhino.UnitSystem.Meters else None,
        'absolute_tolerance':model.Settings.ModelAbsoluteTolerance,
        'object_count':len(model.Objects),'object_types':dict(Counter(type(o.Geometry).__name__ for o in model.Objects)),
        'layers':[{'name':layer.Name,'color':list(layer.Color)} for layer in model.Layers],
        'materials':[], 'embedded_paths':list(model.EmbeddedFilePaths()),'objects':[]
    }
    for material in model.Materials:
        texture = material.GetBitmapTexture()
        info['materials'].append({'name':material.Name,'diffuse_rgba':list(material.DiffuseColor),
                                 'bitmap_path':texture.FileName if texture else None})
    mesh_data = None
    cloud_data = None
    for index, obj in enumerate(model.Objects):
        geometry = obj.Geometry
        ob={'index':index,'type':type(geometry).__name__,'name':obj.Attributes.Name,
            'layer_index':obj.Attributes.LayerIndex,'material_index':obj.Attributes.MaterialIndex}
        if isinstance(geometry,rhino.Mesh):
            vertices,faces,uv=mesh_arrays(geometry)
            ob.update({'vertices':len(vertices),'source_faces':len(geometry.Faces),'triangles':len(faces),
                       'uv_count':len(uv),'vertex_color_count':len(geometry.VertexColors),
                       'normal_count':len(geometry.Normals),'is_closed':geometry.IsClosed,'is_valid':geometry.IsValid,
                       'bbox':bbox(vertices),'topology':topology(vertices,faces),
                       'geometry_sha256':hashlib.sha256(vertices.tobytes()+faces.tobytes()+uv.tobytes()).hexdigest()})
            welded_vertices, inverse = np.unique(np.round(vertices,6),axis=0,return_inverse=True)
            ob['welded_topology_at_1um'] = topology(welded_vertices,inverse[faces])
            mesh_data = vertices,faces,uv
        elif isinstance(geometry,rhino.PointCloud):
            cloud_data=np.asarray([(v.X,v.Y,v.Z) for v in geometry.GetPoints()],dtype=np.float64)
            ob.update({'points':geometry.Count,'bbox':bbox(cloud_data),'has_colors':geometry.ContainsColors})
        else:
            bounds=geometry.GetBoundingBox()
            ob['bbox']={'min':[bounds.Min.X,bounds.Min.Y,bounds.Min.Z],'max':[bounds.Max.X,bounds.Max.Y,bounds.Max.Z]}
        info['objects'].append(ob)
    if digest(path)!=before:
        raise RuntimeError('Cambió un original durante la inspección')
    return info,model,mesh_data,cloud_data


def write_initial_report(reports):
    lines=['# Análisis de escaneos 3D','',
           'Inspección de lectura con rhino3dm '+rhino.__version__+'. Los archivos originales no se modifican.',
           '','La clasificación semántica y la alineación se completarán tras inspeccionar vistas de Blender; no se deducen links sólo del color.','']
    for info in reports:
        lines.extend([f"## {info['file']}",'',f"- Tamaño: {info['bytes']:,} bytes.",
            f"- Formato en disco: archivo 3DM {info['archive_version_on_disk']}; versión normalizada en lector: {info['archive_version_in_reader']}.",
            f"- Aplicación: {info['application_name']} / {info['application_details']}.",
            f"- Unidades declaradas: {info['units']}; escala de unidades a metros: {info['declared_scale_to_meters']}.",
            f"- Objetos: {info['object_count']}; tipos: {info['object_types']}.",
            f"- Materiales: {len(info['materials'])}; texturas embebidas: {len(info['embedded_paths'])}."])
        for obj in info['objects']:
            lines.append(f"- {obj['type']} #{obj['index']}: bounding box {obj['bbox']}.")
            if obj['type']=='Mesh':
                lines.extend([f"  - Vértices: {obj['vertices']}; polígonos: {obj['source_faces']}; triángulos: {obj['triangles']}; UVs: {obj['uv_count']}.",
                    f"  - Componentes indexados: {obj['topology']['connected_components']}; al unificar coordenadas a 1 micrómetro: {obj['welded_topology_at_1um']['connected_components']}. Las costuras UV pueden separar índices aunque la superficie sea continua.",
                    f"  - Cerrada: {obj['is_closed']}; válida: {obj['is_valid']}; aristas de borde: {obj['topology']['boundary_edges']}; no manifold: {obj['topology']['nonmanifold_edges']}; triángulos degenerados: {obj['topology']['degenerate_triangles']}.",
                    f"  - Aristas de borde tras unificar coordenadas sólo para análisis: {obj['welded_topology_at_1um']['boundary_edges']}; componentes: {obj['welded_topology_at_1um']['component_triangle_counts_descending']}.",
                    '  - Estos indicadores no demuestran ausencia de agujeros visuales, deformación o fusión de piezas; la inspección visual es obligatoria.'])
        lines.append('')
    lines.extend(['## Comparación de los dos archivos','',
        f"La geometría triangular y sus UV son idénticas: {reports[0]['objects'][1]['geometry_sha256']==reports[1]['objects'][1]['geometry_sha256']}.",
        'No son dos tomas complementarias; no corresponde superponerlas como nuevas observaciones.',
        '','## Comparación inicial con medidas','',
        'Las unidades son metros. El bounding box global incluye máquina y entorno; no debe forzarse a 0.90 × 0.60 × 0.85 m. La escala se verificará contra la mesa y módulos identificados, con transformaciones rígidas y escala uniforme.',
        '','Fuentes de API: [rhino3dm](https://mcneel.github.io/rhino3dm/python/api/File3dm.html).'])
    report_text = '\n'.join(lines)+'\n'
    (ROOT/'docs'/'scan_analysis_base.md').write_text(report_text,encoding='utf-8')
    # La clasificación manual/visual completa no debe perderse al regenerar derivados.
    completed_report = ROOT/'docs'/'scan_analysis.md'
    if not completed_report.exists():
        completed_report.write_text(report_text,encoding='utf-8')


def main():
    paths=sorted((ROOT/'referencias').glob('*.3dm'))
    inspected=[inspect(path) for path in paths]
    reports=[data[0] for data in inspected]
    (ROOT/'docs'/'scan_analysis.json').write_text(json.dumps({'reader_version':rhino.__version__,'files':reports},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    # Informe escrito ANTES de generar cualquier derivado de malla.
    write_initial_report(reports)
    data=inspected[0]
    info,model,(vertices,faces,uv),cloud=data
    derived=ROOT/'blender'/'derived';derived.mkdir(parents=True,exist_ok=True)
    texture_path=derived/'scan_atlas.png'
    embedded=model.GetEmbeddedFileAsBase64(info['embedded_paths'][0])
    texture_path.write_bytes(base64.b64decode(embedded))
    webots_textures = ROOT/'textures'
    webots_textures.mkdir(exist_ok=True)
    Image.open(texture_path).convert('RGB').save(webots_textures/'scan_atlas.jpg',quality=92,optimize=True)
    np.savez_compressed(derived/'scan_raw.npz',vertices=vertices,faces=faces,uv=uv,point_cloud=cloud)
    obj_path=derived/'scan_raw.obj'
    with obj_path.open('w',encoding='utf-8',newline='\n') as stream:
        stream.write('# Derived from protected 3DM; raw meters, original coordinates\nmtllib scan_raw.mtl\no scan_raw\n')
        for v in vertices: stream.write('v '+' '.join(f'{x:.9g}' for x in v)+'\n')
        for v in uv: stream.write('vt '+' '.join(f'{x:.9g}' for x in v)+'\n')
        stream.write('usemtl ScanAtlas\n')
        for face in faces: stream.write('f '+' '.join(f'{i+1}/{i+1}' for i in face)+'\n')
    (derived/'scan_raw.mtl').write_text('newmtl ScanAtlas\nKd 1 1 1\nKa 0 0 0\nmap_Kd scan_atlas.png\n',encoding='utf-8')
    # Proyecciones de análisis con coordenadas; Blender también genera renders completos.
    atlas=np.asarray(Image.open(texture_path).convert('RGB'))
    sample=uv[faces].mean(axis=1)
    colors=atlas[np.clip(((1-sample[:,1])*(len(atlas)-1)).astype(int),0,len(atlas)-1),
                 np.clip((sample[:,0]*(atlas.shape[1]-1)).astype(int),0,atlas.shape[1]-1)]
    sheet=Image.new('RGB',(1800,800),'#eeeeee');draw=ImageDraw.Draw(sheet)
    for panel,(name,axes,depth,sign) in enumerate([('XZ: frente Y negativo',(0,2),1,-1),('YZ: lateral X positivo',(1,2),0,1),('XY: superior Z positivo',(0,1),2,1)]):
        points=vertices[:,axes];lower=points.min(axis=0);upper=points.max(axis=0)
        factor=min(530/(upper[0]-lower[0]),680/(upper[1]-lower[1]))
        coordinates=np.column_stack(((points[:,0]-lower[0])*factor+panel*600+35,750-(points[:,1]-lower[1])*factor))
        order=np.argsort(vertices[faces,depth].mean(axis=1)*sign)
        for index in order:
            draw.polygon([tuple(point) for point in coordinates[faces[index]]],fill=tuple(int(c) for c in colors[index]))
        draw.text((panel*600+25,15),name,fill='black')
        draw.text((panel*600+25,35),'min '+str(np.round(lower,4))+' / max '+str(np.round(upper,4)),fill='black')
        draw.text((panel*600+25,55),'metros; color muestreado del atlas',fill='black')
    views=ROOT/'docs'/'scan_views';views.mkdir(parents=True,exist_ok=True)
    sheet.save(views/'raw_coordinate_projections.jpg',quality=94)
    print(json.dumps({'scans':[{k:inf[k] for k in ['file','archive_version_on_disk','units','object_count']} for inf in reports],
                      'mesh':reports[0]['objects'][1],'derived':str(derived)},ensure_ascii=False))


if __name__=='__main__':
    main()
