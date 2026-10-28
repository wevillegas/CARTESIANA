"""Background-only CAD mesh preparation. STEP tessellation is handled separately."""
import argparse
import hashlib
import json
from pathlib import Path
import math
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(obj):
    obj.data.calc_loop_triangles()
    return {'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons),
            'triangles': len(obj.data.loop_triangles)}


def bounds(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {'min': lo, 'max': hi, 'dimensions': [hi[i]-lo[i] for i in range(3)]}


def import_obj(path, collection):
    previous = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis='Y', up_axis='Z', validate_meshes=True)
    objects = [obj for obj in bpy.data.objects if obj not in previous and obj.type == 'MESH']
    for obj in objects:
        for old in list(obj.users_collection): old.objects.unlink(obj)
        collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1: bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    # Set render-node colors explicitly; the importer also stores the MTL Kd in diffuse_color.
    for material in obj.data.materials:
        color = tuple(material.diffuse_color)
        if material.node_tree is None:
            material.use_nodes = True
        shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Metallic'].default_value = .65 if color[0] > .6 else .15
        shader.inputs['Roughness'].default_value = .4
    return obj


def export_obj(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=str(path), check_existing=False, forward_axis='Y', up_axis='Z',
                         global_scale=1, apply_transform=True, apply_modifiers=True,
                         export_selected_objects=True, export_triangulated_mesh=True,
                         export_uv=False, export_normals=True, export_materials=False)


def split_materials(obj, destination, stem):
    outputs = []
    for index, material in enumerate(obj.data.materials):
        selected = [p for p in obj.data.polygons if p.material_index == index]
        if not selected: continue
        used = sorted({v for p in selected for v in p.vertices})
        mapping = {v:i for i,v in enumerate(used)}
        mesh = bpy.data.meshes.new(stem + '_' + str(index))
        mesh.from_pydata([obj.data.vertices[v].co for v in used], [],
                         [[mapping[v] for v in p.vertices] for p in selected])
        mesh.update(); mesh.materials.append(material)
        for out, old in zip(mesh.polygons, selected): out.use_smooth = old.use_smooth
        part = bpy.data.objects.new(mesh.name, mesh); destination.objects.link(part)
        rgb = list(material.diffuse_color[:3])
        path = ROOT/'meshes/cad'/(stem + '_material_' + str(index) + '.obj')
        export_obj(part, path)
        outputs.append({'path': path.relative_to(ROOT).as_posix(), 'rgb': rgb, 'material': material.name,
                        'counts': counts(part), 'bytes': path.stat().st_size, 'sha256': sha(path),
                        'bbox_m': bounds(part)})
    return outputs


def render(scene, center, size, path, direction=(2,-3,2)):
    camera = bpy.data.objects.get('CAD_PREVIEW_CAMERA')
    if camera is None:
        camera = bpy.data.objects.new('CAD_PREVIEW_CAMERA', bpy.data.cameras.new('CAD_PREVIEW_CAMERA'))
        scene.collection.objects.link(camera)
    camera.data.type='ORTHO'; camera.data.ortho_scale=size
    camera.location = Vector(center)+Vector(direction).normalized()*size*3
    camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=camera
    scene.render.filepath=str(path); path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.render.render(write_still=True)


def main():
    if not bpy.app.background: raise RuntimeError('Run in factory-startup background, preserving the GUI session')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=95
    scene.world.color=(.13,.15,.18)
    for name,location,power in [('CAD_KEY',(0,-2,3),500),('CAD_FILL',(2,2,2),350)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=2
        light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location
        light.rotation_euler=(Vector((0,0,0))-light.location).to_track_quat('-Z','Y').to_euler()
    groups={name:bpy.data.collections.new(name) for name in ['BECKHOFF_AM3023','REXROTH_CKK','BECKHOFF_AX5203','OPTIONAL_PANEL_COMPONENTS','WEBOTS_EXPORTS']}
    for group in groups.values(): scene.collection.children.link(group)
    config=json.loads((ROOT/'config/cad_processing.json').read_text(encoding='utf-8'))
    report={'blender_version':bpy.app.version_string,'units':'metres','components':[],'exports':[]}
    # Proper rotation: native +Z shaft -> canonical -X; native +Y connectors -> canonical +Z.
    rotation=Matrix(((0,0,-1),(-1,0,0),(0,1,0)))
    prototypes={}
    for spec in config['components']:
        source=ROOT/spec['source_obj']
        obj=import_obj(source,groups['BECKHOFF_AM3023']);obj.name=spec['name']
        before=counts(obj);native_bounds=bounds(obj)
        for vertex in obj.data.vertices:
            vertex.co=rotation@vertex.co+Vector((-.0008,0,0))
        obj.data.update()
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        modifier=obj.modifiers.new('Webots silhouette reduction','DECIMATE')
        modifier.ratio=min(1,spec['target_triangles']/before['triangles'])
        modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        after=counts(obj);prototypes[spec['name']]=obj
        report['components'].append({'name':spec['name'],'source':spec['source_obj'],
            'source_sha256':sha(source),'before':before,'after':after,
            'reduction_percent':100*(1-after['triangles']/before['triangles']),
            'native_bbox_m':native_bounds,'canonical_bbox_m':bounds(obj),
            'origin':'Mounting flange plane; body +X, shaft -X, connectors +Z',
            'uniform_scale':1,'rotation_determinant':rotation.determinant()})
        # Library preview shows the complete motor; no mount or scan is included.
        for other in prototypes.values(): other.hide_render=True
        obj.hide_render=False
        bbox=bounds(obj);center=[(bbox['min'][i]+bbox['max'][i])/2 for i in range(3)]
        render(scene,center,max(bbox['dimensions'])*1.45,ROOT/'docs/cad_views'/(spec['name']+'_blender.jpg'))
        obj.hide_render=True
    integration=json.loads((ROOT/'config/cad_integration.json').read_text(encoding='utf-8'))
    for spec in integration['parts']:
        source=prototypes[spec['component']]
        obj=bpy.data.objects.new(spec['name'],source.data.copy());groups['WEBOTS_EXPORTS'].objects.link(obj)
        matrix=Matrix(spec['rotation_matrix']);translation=Vector(spec['flange_local_m'])
        for vertex in obj.data.vertices:vertex.co=matrix@vertex.co+translation
        obj.data.update();obj.hide_render=True
        meshes=split_materials(obj,groups['WEBOTS_EXPORTS'],spec['name'])
        for mesh in meshes:
            bpy.data.objects[Path(mesh['path']).stem.replace('_material_','_')].hide_render=True
        spec['meshes']=meshes
        report['exports'].append({'name':spec['name'],'solid_def':spec['solid_def'],'enabled':spec['enabled'],
                                  'flange_local_m':spec['flange_local_m'],'rotation_matrix':spec['rotation_matrix'],
                                  'bbox_local_m':bounds(obj),'meshes':meshes})
    # Visible library arrangement, explicit Collections even for unavailable components.
    for index,obj in enumerate(prototypes.values()):obj.hide_render=False;obj.location.y=index*.16
    groups['WEBOTS_EXPORTS'].hide_viewport=True;groups['WEBOTS_EXPORTS'].hide_render=True
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/official_cad_components.blend'),check_existing=False)
    (ROOT/'config/cad_integration.json').write_text(json.dumps(integration,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ROOT/'cad/reports/blender_processing.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'components':len(prototypes),'exports':len(report['exports']),'blend':'blender/official_cad_components.blend'}))


if __name__=='__main__':main()
