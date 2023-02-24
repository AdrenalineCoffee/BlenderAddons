
bl_info = {
    "name": "Modifier++",
    "author": "Evgenii Trunin",
    "blender": (2, 91, 0),
    "version": (1, 0),
    "blender": (2, 91, 0),
    "location": "View 3D > Modifier > Tools",
    "description": "Allows you to add active object modifiers to selected objects without replacing them. Also, all existing modifiers for objects will be preserved.",
    "warning": "",
    "doc_url": "https://github.com/AdrenalineCoffee/BlenderAddons/wiki/Modifier",
    "tracker_url": "https://github.com/AdrenalineCoffee/BlenderAddons/issues",
    "category": "Object",
}

from collections import defaultdict
import bpy
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty

class SharpEdgesFromUvIslands(Operator):
    bl_idname = "object.sharp_edges_from_uv"
    bl_label = "Sharp Edges From UV Islands"
    bl_description = "Add sharp edges on seams"
    
    use_existing_seams: BoolProperty(
        name="Use existing seams",
        default = False,
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        current_mode = context.object.mode
        view_layer = context.view_layer
        act_ob = view_layer.objects.active
        
        selected_ob = list(context.selected_objects)
        mesh_ob = [ob for ob in context.selected_objects if ob.type == 'MESH']
        initial_selection = defaultdict(set)
        
        if not mesh_ob:
            return {'FINISHED'}

        for ob in selected_ob:
            if ob.type != 'MESH':
                ob.select_set(state=False)
                
        view_layer.objects.active = mesh_ob[0]
        bpy.ops.object.mode_set(mode='EDIT')
        
        for ob in mesh_ob:
            me = ob.data
            bm = bmesh.from_edit_mesh(me)
            uv = bm.loops.layers.uv.verify()
            view_layer.objects.active = ob
            
            bpy.ops.mesh.customdata_custom_splitnormals_clear()

            for f in bm.faces:
                f.smooth = True  # Set all faces shaded smooth
                for l in f.loops:
                    l.edge.smooth = True  # Remove all sharp edges
                    if l[uv].select:
                        initial_selection[ob].add(l.index)
                        
            ob.data.use_auto_smooth = True
            ob.data.auto_smooth_angle = 3.14159
            
        bpy.ops.uv.reveal()
        bpy.ops.uv.select_all(action='SELECT')
        if not self.use_existing_seams:
            bpy.ops.uv.seams_from_islands(mark_seams=False, mark_sharp=True)
            
        for ob in selected_ob:
            ob.select_set(state=True)
        view_layer.objects.active = act_ob
        
        for ob in context.objects_in_mode_unique_data:
            me = ob.data
            bm = bmesh.from_edit_mesh(me)
            uv = bm.loops.layers.uv.verify()

            for f in bm.faces:
                for l in f.loops:
                    if l.index in initial_selection[ob]:
                        continue
                    l[uv].select = False
            if self.use_existing_seams:
                for e in bm.edges:
                    if e.seam:
                        e.smooth = False
        bpy.ops.object.mode_set(mode=current_mode)
        return {'FINISHED'}
 
#_______________________________________

class ModifAdd(Operator):
    bl_idname = 'object.modif_add'
    bl_label = "Add To Selected"
    bl_description = "Copy and add modifier from active object to selected"
    change_even = None
    
    def structure():
        pass
        
    def execute (self, context) -> set:
        
        active_object = bpy.context.object
        selected_objects = [o for o in bpy.context.selected_objects
                            if o != active_object and o.type == active_object.type]

        for obj in selected_objects:
            for mSrc in active_object.modifiers:
                mDst = obj.modifiers.get(mSrc.name, None)
                if not mDst:
                    mDst = obj.modifiers.new(mSrc.name, mSrc.type)

                # collect names of writable properties
                properties = [p.identifier for p in mSrc.bl_rna.properties
                              if not p.is_readonly]

                # copy those properties
                for prop in properties:
                    setattr(mDst, prop, getattr(mSrc, prop))
        
        return {"FINISHED"} 
#___________________________________________

class ModifExp(Operator):
    bl_idname = 'object.modif_exp'
    bl_label = "Export Modifier"
    bl_description = "Add modifier for the export HardSurf bake pipeline!"
    change_even = None

    def structure():
        pass
        
    def execute (self, context) -> set:
        sel = bpy.context.selected_objects
        print('\n'+str(sel))
        
        for obj in sel:
            if obj.type == 'MESH':
                our_modif = obj.modifiers.keys()
                triang = True
                weight = True
                
                for mod in our_modif:
                    if mod.find('Triangulate') != -1: triang = False
                    if mod.find('Weighted Normal') != -1: weight = False
                
                if triang == True:
                    mod1 = obj.modifiers.new("Triangulate", 'TRIANGULATE')
                    mod1.keep_custom_normals = True
                    
                if weight == True:
                    mod2 = obj.modifiers.new("Weighted Normal", 'WEIGHTED_NORMAL')
                    mod2.keep_sharp = True
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True) #Apply all transforms
                bpy.ops.object.sharp_edges_from_uv()
                
        return {"FINISHED"} 
    
#____________________________________________________

def extended_menu(self, context):
    if (context.active_object):
        if (len(context.active_object.modifiers)):
            col = self.layout.column(align=True)

          # original ops
            row = col.row(align=True)
            row.operator("object.apply_all_modifiers", icon='IMPORT', text="Apply All")
            row.operator("object.delete_all_modifiers", icon='X', text="Delete All")
 
            row = col.row(align=True)
            row.operator("object.toggle_apply_modifiers_view", icon='RESTRICT_VIEW_OFF', text="Viewport Vis")
            row.operator("wm.toggle_all_show_expanded", icon='FULLSCREEN_ENTER', text="Toggle Stack")
                                         
          # custom ops
            row = col.row(align=True)                          
            row.operator('object.modif_add', icon="SNAP_ON")
            row.operator('object.modif_exp', icon = 'SHADERFX')  

#____________________________________________

classes = [
    SharpEdgesFromUvIslands,
    ModifAdd,
    ModifExp
]

def register():
    for cl in reversed(classes):
        bpy.utils.register_class(cl)

    # check if addon is enabled
    if 'space_view3d_modifier_tools' in bpy.context.preferences.addons.keys(): 
        # get panel
        panel_class = eval("bpy.types.DATA_PT_modifiers")
        # check if 'extended_menu' already in draw_funcs to prevent double entries
        if not [f for f in panel_class.draw._draw_funcs if f.__name__ == 'extended_menu']:
            #print("No load menu")
            # add extended menu first (with registered original ops)  
            panel_class.prepend(extended_menu)                                            
            # remove original menu 
            old_menu = [f for f in bpy.types.DATA_PT_modifiers.draw._draw_funcs if f.__name__ == 'menu'][0]
            panel_class.draw._draw_funcs.remove(old_menu)
    else: bpy.types.DATA_PT_modifiers.prepend(extended_menu)

def unregister():
    for cl in reversed(classes):
        bpy.utils.register_class(cl)
        
if __name__ == '__main__': 
    register()
    