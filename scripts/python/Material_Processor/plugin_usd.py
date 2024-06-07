import pxr
import hou


class USD_Shaders():
    def __init__(self):
        pass

    def get_connected_file_path(self, shader_input):
        """ Recursively follow shader input connections to find the actual file path. """
        connection = shader_input.GetConnectedSource()
        while connection:
            connected_shader_api, connected_input_name, _ = connection
            connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())
            connected_input = connected_shader.GetInput(connected_input_name)

            if connected_input and connected_input.HasConnectedSource():
                connection = connected_input.GetConnectedSource()
            else:
                return connected_input.Get()

    def traverse_shader_network(self, shader, material_name, texture_data, path=[], connected_param=""):
        if shader is None:
            return

        shader_prim = shader.GetPrim()
        # print(f'{shader=}, {shader_prim=}')
        shader_id = shader_prim.GetAttribute('info:id').Get()
        path.append(shader_id or shader_prim.GetPath().GetName())

        # Handle UsdUVTexture nodes (texture nodes)
        if shader_id == 'UsdUVTexture':
            file_path_attr = shader.GetInput('file')
            if file_path_attr and isinstance(file_path_attr, pxr.UsdShade.Input):
                print(f'UsdUVTexture found: {shader_prim}, file_path_attr: {file_path_attr}')

                # Get the actual file path by following connections
                attr_value = self.get_connected_file_path(file_path_attr)

                if isinstance(attr_value, pxr.Sdf.AssetPath):
                    file_path = attr_value.resolvedPath if attr_value.resolvedPath else attr_value.path
                    # print(f'Resolved file path: {file_path}')
                    if file_path:
                        texture_data.append({
                            'material_name': material_name,
                            'texture_type': shader_id,
                            'file_path': file_path,
                            'traversal_path': ' -> '.join(path),
                            'connected_input': connected_param
                        })
                        # print(f'Texture data appended: {texture_data[-1]}')
                    else:
                        print(f'Empty file path for asset: {attr_value}')
                else:
                    print(f'Invalid asset path type: {type(attr_value)}')
            else:
                print(f'File path attribute is not found or not connected for {shader_prim}')
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

                # Use self to call the method recursively
                self.traverse_shader_network(connected_shader, material_name, texture_data, path, connected_param)

        path.pop()

    def find_usd_preview_surface_shader(self, material):
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

                # Debug print for each material
                # print(f"Found Material: {material_name}")

                # Find the UsdPreviewSurface shader and start traversal from its inputs
                surface_shader = self.find_usd_preview_surface_shader(material)
                if surface_shader:
                    print(f"Found UsdPreviewSurface Shader: {surface_shader}")
                    for input in surface_shader.GetInputs():
                        self.traverse_shader_network(surface_shader, material_name, texture_data)
                else:
                    print(f"No UsdPreviewSurface Shader found for material: {material_name}")

        return texture_data

    def create_principled_shaders_with_textures(self, texture_data):
        mat_context = hou.node("/mat")
        if not mat_context:
            raise ValueError("'/mat' context not found in Houdini.")

        if not texture_data:
            print("No texture data found to create shaders.")  # Debug print
            return

        for texture_info in texture_data:
            material_name = texture_info['material_name']
            file_path = texture_info['file_path']
            connected_input = texture_info['connected_input']

            # Create or find the shader node
            shader_node = mat_context.node(material_name)
            if not shader_node:
                shader_node = mat_context.createNode('principledshader::2.0', node_name=material_name)
                print(f"Created shader node: {shader_node}")  # Debug print

            # Map textures based on the connected input
            if connected_input == 'diffuseColor':
                shader_node.parm('basecolor_texture').set(file_path)
                shader_node.parm('basecolor_useTexture').set(True)
                shader_node.parm('basecolor_usePointColor').set(0)
                shader_node.parmTuple('basecolor').set((1, 1, 1))
            elif connected_input == 'normal':
                shader_node.parm('baseNormal_texture').set(file_path)
                shader_node.parm('baseNormal_useTexture').set(True)
                shader_node.parm('baseBumpAndNormal_enable').set(True)
            elif connected_input == 'metallic':
                shader_node.parm('metallic_texture').set(file_path)
                shader_node.parm('metallic_useTexture').set(True)
                shader_node.parm('metallic').set(1)
            elif connected_input == 'occlusion':
                shader_node.parm('occlusion_texture').set(file_path)
                shader_node.parm('occlusion_useTexture').set(True)
            elif connected_input == 'roughness':
                shader_node.parm('rough_texture').set(file_path)
                shader_node.parm('rough_useTexture').set(True)
                shader_node.parm('rough').set(1)
            # Add more conditions as needed for other textures

            # Layout nodes for better visualization
            mat_context.layoutChildren()


def run():
    # Example usage
    classMC = USD_Shaders()
    textures = classMC.extract_textures_from_shaders()

    # print(f"Extracted Textures: {textures}")  # Debug print

    # classMC.create_principled_shaders_with_textures(textures)
    classMC.create_principled_shaders_with_textures(textures)
