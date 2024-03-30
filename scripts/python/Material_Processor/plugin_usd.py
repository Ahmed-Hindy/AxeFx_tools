import pxr
import hou


class USD_Shaders():
    def __init__(self):
        pass
        # self.stage = stage


    def traverse_shader_network(shader, material_name, texture_data, path=[], connected_param=""):
        if shader is None:
            return

        shader_prim = shader.GetPrim()
        shader_id = shader_prim.GetAttribute('info:id').Get()
        path.append(shader_id or shader_prim.GetPath().GetName())

        # Handle UsdUvTexture nodes (texture nodes)
        if shader_id == 'UsdUVTexture':
            file_path_attr = shader.GetInput('file')
            if file_path_attr and not file_path_attr.HasConnectedSource():
                asset_path = file_path_attr.Get()
                if isinstance(asset_path, pxr.Sdf.AssetPath):
                    file_path = asset_path.resolvedPath if asset_path.resolvedPath else asset_path.path
                    texture_data.append({
                        'material_name': material_name,
                        'texture_type': shader_id,
                        'file_path': file_path,
                        'traversal_path': ' -> '.join(path),
                        'connected_input': connected_param
                    })
                    # Print the connected parameter name
                    # print(f"Texture: {shader_id}, Connected to: {connected_param}")
            path.pop()
            return

        # Recursive traversal for UsdPreviewSurface or other shaders
        for input in shader.GetInputs():
            connection_info = input.GetConnectedSource()
            if connection_info:
                connected_shader_api, source_name, _ = connection_info
                connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())

                # If it's connected to a UsdPreviewSurface, track the input name
                if shader_id == 'UsdPreviewSurface':
                    connected_param = input.GetBaseName()

                USD_Shaders.traverse_shader_network(connected_shader, material_name, texture_data, path.copy(), connected_param)

        path.pop()
        
    # This function should be called within the context of the extract_textures_from_shaders function

    def find_usd_preview_surface_shader(material):
        for shader_output in material.GetOutputs():
            connection = shader_output.GetConnectedSource()
            if connection:
                connected_shader_api, _, _ = connection
                connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())
                shader_id = connected_shader.GetPrim().GetAttribute('info:id').Get()
                if shader_id == 'UsdPreviewSurface':
                    return connected_shader
        return None
    
    def extract_textures_from_shaders(self):
        # Get the currently selected nodes
        selected_nodes = hou.selectedNodes()

        # Check if there is at least one selected node and it's a LOP node
        if not selected_nodes or not isinstance(selected_nodes[0], hou.LopNode):
            raise ValueError("Please select a LOP node.")

        # Get the stage from the selected LOP node
        stage = selected_nodes[0].stage()
        if not stage:
            raise ValueError("Failed to access USD stage from the selected node.")

        texture_data = []

        for prim in stage.Traverse():
            if prim.IsA(pxr.UsdShade.Material):
                material = pxr.UsdShade.Material(prim)
                material_name = material.GetPath().name

                # Find the UsdPreviewSurface shader and start traversal from its inputs
                surface_shader = find_usd_preview_surface_shader(material)
                if surface_shader:
                    for input in surface_shader.GetInputs():
                        traverse_shader_network(surface_shader, material_name, texture_data)

        return texture_data





        
    def create_principled_shaders_with_textures(self, texture_data):
        mat_context = hou.node("/mat")
        if not mat_context:
            raise ValueError("'/mat' context not found in Houdini.")

        for texture_info in texture_data:
            material_name = texture_info['material_name']
            file_path = texture_info['file_path']
            connected_input = texture_info['connected_input']

            # Create or find the shader node
            shader_node = mat_context.node(material_name)
            if not shader_node:
                shader_node = mat_context.createNode('principledshader::2.0', node_name=material_name)

            # Map textures based on the connected input
            if connected_input == 'diffuseColor':
                shader_node.parm('basecolor_texture').set(file_path)
                shader_node.parm('basecolor_useTexture').set(True)
                shader_node.parm('basecolor_usePointColor').set(0)
                shader_node.parmTuple('basecolor').set((1,1,1))
            elif connected_input == 'normal':
                shader_node.parm('baseNormal_texture').set(file_path)
                shader_node.parm('baseNormal_useTexture').set(True)
                shader_node.parm('baseBumpAndNormal_enable').set(True)
            elif connected_input == 'metallic':
                # Set the metallic texture parameter (assuming it exists)
                shader_node.parm('metallic_texture').set(file_path)
                shader_node.parm('metallic_useTexture').set(True)
                shader_node.parm('metallic').set(1)
            elif connected_input == 'occlusion':
                # Set the occlusion texture parameter (assuming it exists)
                shader_node.parm('occlusion_texture').set(file_path)
                shader_node.parm('occlusion_useTexture').set(True)
            elif connected_input == 'roughness':
                shader_node.parm('rough_texture').set(file_path)
                shader_node.parm('rough_useTexture').set(True)
                shader_node.parm('rough').set(1)
            # Add more conditions as needed for other textures

            # Layout nodes for better visualization
            mat_context.layoutChildren()


    def create_redshift_materials_with_textures(self, texture_data):
        mat_context = hou.node("/mat")
        if not mat_context:
            raise ValueError("'/mat' context not found in Houdini.")

        for texture_info in texture_data:
            material_name = texture_info['material_name']
            file_path = texture_info['file_path']
            connected_input = texture_info['connected_input']

            # Create or find the Redshift material node
            rs_material_node = mat_context.node(material_name)
            if not rs_material_node:
                rs_material_node = mat_context.createNode('rs_usd_material_builder', node_name=material_name)

            # Find or create the Redshift Standard Material inside the builder
            rs_standard_material = rs_material_node.node('StandardMaterial1')
            
            # Create a TextureSampler for each texture
            texture_sampler = rs_material_node.createNode('redshift::TextureSampler')
            print(f"==>> texture_sampler: {texture_sampler}")
            texture_sampler.parm('tex0').set(file_path)

            # Connect the TextureSampler to the StandardMaterial based on the connected input
            if connected_input == 'diffuseColor':
                texture_sampler.outputConnectors()[0].connectToInput(rs_standard_material.inputConnectors()['diffuse_color'])
            elif connected_input == 'normal':
                texture_sampler.outputConnectors()[0].connectToInput(rs_standard_material.inputConnectors()['bump_input'])
            elif connected_input == 'roughness':
                texture_sampler.outputConnectors()[0].connectToInput(rs_standard_material.inputConnectors()['refl_roughness'])
            # Add more conditions as needed for other textures

            # Layout nodes for better visualization
            mat_context.layoutChildren()





