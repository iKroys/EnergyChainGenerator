bl_info = {
    "name": "Energy Chain Generator",
    "blender": (4, 0, 0),
    "category": "Add Mesh",
    "description": "Generate an energy chain with a curve, armature, and linked objects",
    "author": "Ćiril Studenović (iKroys)",
    "version": (1, 0),
    "warning": "",
    "wiki_url": "https://github.com/iKroys/EnergyChainGenerator",
    "tracker_url": "https://github.com/iKroys/EnergyChainGenerator/issues",
    "license": "CC BY-NC-ND 4.0",
}

# Energy Chain Generator Addon
# Author: Ćiril Studenović (iKroys)
# License: CC BY-NC-ND 4.0
# Original Repository: https://github.com/iKroys/EnergyChainGenerator
# Attribution: If you use or share this addon, please include the author's name and link to the original repository.

import bpy
import bmesh
import math
import mathutils

class OBJECT_OT_calculate_head_offset(bpy.types.Operator):
    bl_idname = "object.calculate_head_offset"
    bl_label = "Calculate Bone Head Offset"
    bl_description = "Calculate the Bone Head Offset based on the cursor position"

    def execute(self, context):
        custom_object = context.window_manager.custom_object
        cursor_y = bpy.context.scene.cursor.location.y

        if not custom_object:
            self.report({'ERROR'}, "No custom object selected.")
            return {'CANCELLED'}

        y_start = custom_object.location.y - (custom_object.dimensions.y / 2)
        head_offset = cursor_y - y_start
        context.window_manager.bone_head_offset = round(head_offset, 4)

        self.report({'INFO'}, f"Bone Head Offset set to {head_offset:.4f}")
        return {'FINISHED'}


class OBJECT_OT_calculate_tail_offset(bpy.types.Operator):
    bl_idname = "object.calculate_tail_offset"
    bl_label = "Calculate Bone Tail Offset"
    bl_description = "Calculate the Bone Tail Offset based on the cursor position"

    def execute(self, context):
        custom_object = context.window_manager.custom_object
        cursor_y = bpy.context.scene.cursor.location.y

        if not custom_object:
            self.report({'ERROR'}, "No custom object selected.")
            return {'CANCELLED'}

        y_end = custom_object.location.y + (custom_object.dimensions.y / 2)
        tail_offset = cursor_y - y_end
        context.window_manager.bone_tail_offset = round(tail_offset, 4)

        self.report({'INFO'}, f"Bone Tail Offset set to {tail_offset:.4f}")
        return {'FINISHED'}


class OBJECT_OT_generate_energy_chain(bpy.types.Operator):
    bl_idname = "object.generate_energy_chain"
    bl_label = "Generate Energy Chain"
    bl_description = "Generate an energy chain with a curve, armature, and linked objects"
    
    radius: bpy.props.FloatProperty(
        name="Radius",
        description="Radius of arc",
        default=1.0,
        min=0.01,
    )
    length: bpy.props.FloatProperty(
        name="Length",
        description="Length of Energy Chain",
        default=2.0,
        min=0.0,
    )
    
    def get_unique_name(self, base_name):
        """Generate a unique name by appending a number if needed."""
        existing_names = {obj.name for obj in bpy.data.objects}
        if base_name not in existing_names:
            return base_name
        index = 1
        while f"{base_name}.{index:03}" in existing_names:
            index += 1
        return f"{base_name}.{index:03}"    
    
    def execute(self, context):
        # Get the custom object and input values
        custom_object = context.window_manager.custom_object
        link_count = context.window_manager.link_count
        change_bone_size = context.window_manager.change_bone_size
        head_offset = context.window_manager.bone_head_offset
        tail_offset = context.window_manager.bone_tail_offset
        
        if not custom_object:
            self.report({'ERROR'}, "No custom object selected.")
            return {'CANCELLED'}

        # Step 1: Get the object's Y dimension
        y_dimension = custom_object.dimensions.y
        if y_dimension <= 0:
            self.report({'ERROR'}, "Custom object has an invalid Y-dimension.")
            return {'CANCELLED'}
        
#-------------------------------------------------------------------------------------------------------------------------------------------------#        
#--------------------------------------------------------- U-SHAPE CURVE GENERATOR ---------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------------------------------------------------#        
        # This part generates U shape curve according to inputs
        # Ensure we are in Object Mode
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
                
        # Retrieve radius and length
        radius = self.radius
        length = self.length
        
        # Calculate arc length and check validity
        arc_length = math.pi * radius
        print(self, radius, length)
        if length <= arc_length:
            self.report({'WARNING'}, f"Length must be greater than arc length ({arc_length:.3f}).")
            return {'CANCELLED'}
        
        # Step 1: Add a circle
        curve_name = self.get_unique_name("U_Shape")
        curve = bpy.ops.mesh.primitive_circle_add(radius=radius, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, 1.5708, 0), scale=(1, 1, 1))
        curve = bpy.context.active_object
        curve.name = curve_name
        if curve is None:
            self.report({'ERROR'}, "Failed to create curve.")
            return {'CANCELLED'}
        
        # Step 2: Edit the mesh and delete half of the circle
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(curve.data)
        verts_to_delete = [v for v in bm.verts if v.co.y < 0]
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
        bmesh.update_edit_mesh(curve.data)

        # Step 3: Select first and last vertices
        bpy.ops.mesh.select_all(action='DESELECT')
        bm.verts.ensure_lookup_table()
        min_x_vert = min(bm.verts, key=lambda v: v.co.x)
        max_x_vert = max(bm.verts, key=lambda v: v.co.x)
        min_x_vert.select = True
        max_x_vert.select = True
        bmesh.update_edit_mesh(curve.data)

        # Step 4: Extrude vertices
        arcLength = radius * math.pi
        extrudeAmount = (length - arcLength) / 2
        bpy.ops.mesh.extrude_vertices_move(TRANSFORM_OT_translate={"value": (0, -extrudeAmount, 0)})
        bpy.ops.object.mode_set(mode='OBJECT')

        # Step 5: Convert to Curve
        uCurve = bpy.ops.object.convert(target='CURVE')
        
        # Step 6: Add Hook modifier to curve
        bpy.ops.object.modifier_add(type='HOOK')
        
        #Step 7: Add Empty Single Arrow
        controller = bpy.ops.object.empty_add(type='SINGLE_ARROW', align='WORLD', location=(0, 0, 0), rotation=(1.5708, 0, 0), scale=(1, 1, 1))
        controller = bpy.context.active_object
        controller.name = self.get_unique_name("Controller")
        
        # Step 8: Select U shape curve
        bpy.ops.object.select_all(action='DESELECT')
        curve.select_set(True)
        bpy.context.view_layer.objects.active = curve  
        
        # Select only the half-circle vertices (Y = 0 plane)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='DESELECT')
        for spline in curve.data.splines:
            if spline.type == 'POLY':  # Ensure we are working with poly splines
                for i, point in enumerate(spline.points):
                    # Select only the first half of the vertices (indices 0 to mid-point)
                    if 0 < i < (len(spline.points)-1):  
                        point.select = True
        
        # Assign controlles as object in hook modifier                        
        bpy.context.object.modifiers["Hook"].object = controller
        
        # Activates and execute Assign button from hook modifier to assign current selected vertices to controller
        bpy.ops.object.hook_assign()
        
        # Go back to object mode and deselect all
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT') 
        
#-------------------------------------------------------------------------------------------------------------------------------------------------#        
#--------------------------------------------------------- BONE AND LINK GENERATOR ---------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------------------------------------------------#
        # Step 1: Calculate bone length and starting position
        bone_length = y_dimension + tail_offset - head_offset if change_bone_size else y_dimension
        start_y = custom_object.location.y - (y_dimension / 2)

        # Step 2: Create Armature at the starting position
        if change_bone_size:
            bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, start_y + head_offset, 0))
        else:
            bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, start_y, 0))
        armature = bpy.context.active_object
        armature.name = self.get_unique_name("EnergyChainArmature")
        #armature.data.name = armature.name

        # Step 3: Remove the default bone
        bpy.ops.armature.select_all(action='SELECT')
        bpy.ops.armature.delete()

        # Step 4: Generate bones
        prev_bone = None
        bones = []
        for i in range(link_count):
            bone = armature.data.edit_bones.new(armature.name + f"_Bone{i + 1}")
            bone.head = (0, i * bone_length, 0)
            bone.tail = (0, (i + 1) * bone_length, 0)

            if prev_bone:
                bone.parent = prev_bone
                bone.use_connect = True
            prev_bone = bone
            bones.append(bone)

        # Step 5: Return to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Step 6: Duplicate the custom object for each bone
        new_link_name = armature.name.replace("Armature", "Link")
        links = []
        for i in range(link_count):
            new_link = custom_object.copy()
            new_link.data = custom_object.data.copy()
            new_link.name = new_link_name + f"_{i + 1}"
            new_link.location = (0, i * bone_length, 0) 
            bpy.context.collection.objects.link(new_link)
            links.append(new_link)

        # Hide the original object
        custom_object.hide_set(True)

        # Step 7: Parent each link to its corresponding bone
        # Prefixes or naming convention for bones and objects
        bone_prefix = armature.name + "_Bone"  # Replace with your bone name prefix
        object_prefix = new_link_name  # Replace with your object name prefix
        
        # Step 8: Iterate through all the bones and objects
        for i in range(1, link_count+1):  # Adjust the range to match your count            
            bone_name = f"{bone_prefix}{i}"
            object_name = f"{object_prefix}_{i}"
            
            # Ensure both the bone and object exist
            if bone_name in armature.data.bones and object_name in bpy.data.objects:
                obj = bpy.data.objects[object_name]
                
                # Deselect all objects
                bpy.ops.object.select_all(action='DESELECT')

                # Select the object to be parented
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj  # Make it the active object

                # Enter Pose Mode for the armature
                bpy.context.view_layer.objects.active = armature  # Make the armature active
                bpy.ops.object.mode_set(mode='POSE')

                # Select the specific bone in Pose Mode
                armature.data.bones.active = armature.data.bones[bone_name]

                # Switch back to Object Mode and ensure the object is selected
                bpy.ops.object.mode_set(mode='OBJECT')
                obj.select_set(True)
                armature.select_set(True)
                bpy.context.view_layer.objects.active = armature

                # Perform parenting with 'Keep Transform'
                bpy.ops.object.parent_set(type='BONE', keep_transform=True)
                
                print(f"Parented {object_name} to {bone_name}")
            else:
                print(f"Skipping {object_name} or {bone_name}: Not found.")

        print("Parenting complete!")
        
        # Step 9: Add Spline IK Constraint to the last bone
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
        last_bone_name = armature.pose.bones[-1].name
        last_bone = armature.pose.bones[last_bone_name]
        
        # Add Spline IK Constraint
        spline_ik = last_bone.constraints.new(type='SPLINE_IK')
        spline_ik.name = "Spline IK"
        spline_ik.target = curve  # Set the U-Shape curve as the target
        spline_ik.chain_count = link_count   

        # Set Scaling Modes
        spline_ik.y_scale_mode = 'BONE_ORIGINAL'
        spline_ik.xz_scale_mode = 'BONE_ORIGINAL'        
        
        # Return to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # At the end we set parents of controller and curve
        bpy.ops.object.select_all(action='DESELECT')
        
        # Setting controller parent
        controller.select_set(True)
        curve.select_set(True)
        bpy.context.view_layer.objects.active = curve
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

        # Setting curve parent        
        bpy.ops.object.select_all(action='DESELECT')
        curve.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        bpy.ops.object.select_all(action='DESELECT')
        
        self.report({'INFO'}, "Energy chain generated successfully.")
        return {'FINISHED'}


class VIEW3D_PT_energy_chain_panel(bpy.types.Panel):
    bl_label = "Energy Chain Generator"
    bl_idname = "VIEW3D_PT_energy_chain_generator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Energy Chain Generator'

    def draw(self, context):
        layout = self.layout
        
        # Add inputs for curve radius and length
        layout.label(text="Curve Properties:")
        layout.prop(context.window_manager, "u_shape_radius", text="Radius")
        layout.prop(context.window_manager, "u_shape_length", text="Length")

        # Add custom object drag-and-drop input
        layout.label(text="Custom Object:")
        layout.prop(context.window_manager, "custom_object", text="")
        layout.prop(context.window_manager, "link_count", text="Link Count")

        layout.prop(context.window_manager, "change_bone_size", text="Change Bone Size")
        if context.window_manager.change_bone_size:
            row = layout.row(align=True)
            row.prop(context.window_manager, "bone_head_offset", text="Bone Head Offset")
            row.operator("object.calculate_head_offset", text="", icon="CURSOR")
            
            row = layout.row(align=True)
            row.prop(context.window_manager, "bone_tail_offset", text="Bone Tail Offset")
            row.operator("object.calculate_tail_offset", text="", icon="CURSOR")

        op = layout.operator("object.generate_energy_chain", text="Generate Energy Chain")
        op.radius = context.window_manager.u_shape_radius
        op.length = context.window_manager.u_shape_length

# Register and Unregister Classes
def register():
    bpy.utils.register_class(OBJECT_OT_calculate_head_offset)
    bpy.utils.register_class(OBJECT_OT_calculate_tail_offset)
    bpy.utils.register_class(OBJECT_OT_generate_energy_chain)
    bpy.utils.register_class(VIEW3D_PT_energy_chain_panel)
    bpy.types.WindowManager.u_shape_radius = bpy.props.FloatProperty(
        name="Radius",
        description="Radius of the half-circle",
        default=1.0,
        min=0.01,
    )
    bpy.types.WindowManager.u_shape_length = bpy.props.FloatProperty(
        name="Length",
        description="Length of the straight lines extending from the half-circle",
        default=2.0,
        min=0.0,
    )
    bpy.types.WindowManager.custom_object = bpy.props.PointerProperty(
        name="Custom Object",
        description="Drag and drop a custom object here",
        type=bpy.types.Object,
    )
    bpy.types.WindowManager.link_count = bpy.props.IntProperty(
        name="Link Count",
        description="Number of bones to generate in the armature",
        default=1,
        min=1,
    )
    bpy.types.WindowManager.change_bone_size = bpy.props.BoolProperty(
        name="Change Bone Size",
        description="Enable to change bone head and tail offsets",
        default=False,
    )
    bpy.types.WindowManager.bone_head_offset = bpy.props.FloatProperty(
        name="Bone Head Offset",
        description="Offset for bone head position on Y-axis",
        default=0.0,
    )
    bpy.types.WindowManager.bone_tail_offset = bpy.props.FloatProperty(
        name="Bone Tail Offset",
        description="Offset for bone tail position on Y-axis",
        default=0.0,
    )

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_calculate_head_offset)
    bpy.utils.unregister_class(OBJECT_OT_calculate_tail_offset)
    bpy.utils.unregister_class(OBJECT_OT_generate_energy_chain)
    bpy.utils.unregister_class(VIEW3D_PT_energy_chain_panel)
    del bpy.types.WindowManager.u_shape_radius
    del bpy.types.WindowManager.u_shape_length
    del bpy.types.WindowManager.custom_object
    del bpy.types.WindowManager.link_count
    del bpy.types.WindowManager.change_bone_size
    del bpy.types.WindowManager.bone_head_offset
    del bpy.types.WindowManager.bone_tail_offset

if __name__ == "__main__":
    register()
