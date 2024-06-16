"""
Copyright Ahmed Hindy. Please mention the author if you found any part of this code useful.

"""
from importlib import reload
import json
try:
    import hou
    from Material_Processor import materials_processer  # why do we have to do this in Houdini if they both exist in the same directoy!!!
except:
    import materials_processer

reload(materials_processer)
import pxr
from pxr import Usd, UsdShade, Sdf


class USD_Shaders():
    def __init__(self):
        pass

    def _get_connected_file_path(self, shader_input):
        """
        Recursively follow shader input connections to find the actual file path.
        :param shader_input: <pxr.UsdShade.Input object>. which we get from <UsdShade.Shader object>.GetInput('file')
        """
        connection = shader_input.GetConnectedSource()
        # print(f'///{shader_input.Get().path=}\n{connection=}\n')
        while connection:
            connected_shader_api, connected_input_name, _ = connection
            connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())
            connected_input = connected_shader.GetInput(connected_input_name)

            if connected_input and connected_input.HasConnectedSource():
                connection = connected_input.GetConnectedSource()
            else:
                return connected_input.Get()


    def traverse_shader_network(self, shader, material_name, texture_data, path=[], connected_param=""):
        """
        main traversal function.
        :param shader: <UsdShade.Shader object> e.g. Usd.Prim(</root/material/_03_Base/UsdPreviewSurface/ShaderUsdPreviewSurface>)
        :param material_name: str material name. e.g. '_01_Head', '_02_Body', or '_03_Base'
        :param texture_data: recursive texture data that is gotten from same function. left empty when run from outside.
        :param path: left empty when run from outside.
        :param connected_param: left empty when run from outside.
        """
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

                # get the sdf.AssetPath if it already exists on prim
                attr_value = file_path_attr.Get()
                print(f'///{attr_value=}\n')
                if not attr_value:
                    # if no sdf.AssetPath, then get it from connected inputs
                    attr_value = self._get_connected_file_path(file_path_attr)
                if not isinstance(attr_value, pxr.Sdf.AssetPath):
                    print(f'Invalid asset path type: {type(attr_value)}')
                    return

                file_path = attr_value.resolvedPath if attr_value.resolvedPath else attr_value.path
                print(f'Resolved file path: {file_path}')
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
                print(f'File path attribute is not found or not connected for {shader_prim}')
            path.pop()
            return

        # Recursive traversal for UsdPreviewSurface
        for input in shader.GetInputs():
            connection_info = input.GetConnectedSource()
            if connection_info:
                connected_shader_api, source_name, _ = connection_info
                connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())

                # If it's connected to a UsdPreviewSurface, track the input name
                if shader_id == 'UsdPreviewSurface':
                    connected_param = input.GetBaseName()

                # call the method recursively
                self.traverse_shader_network(connected_shader, material_name, texture_data, path, connected_param)

        path.pop()

    def find_usd_preview_surface_shader(self, material):
        for shader_output in material.GetOutputs():
            connection = shader_output.GetConnectedSource()
            print(f'///{connection=}')
            if connection:
                connected_shader_api, _, _ = connection
                connected_shader = pxr.UsdShade.Shader(connected_shader_api.GetPrim())
                shader_id = connected_shader.GetPrim().GetAttribute('info:id').Get()
                if shader_id == 'UsdPreviewSurface':
                    return connected_shader
        return None


    def get_all_usdpreview_mats_from_stage(self, stage):
        materials_found = []
        for prim in stage.Traverse():
            if prim.IsA(pxr.UsdShade.Material):
                material = pxr.UsdShade.Material(prim)
                materials_found.append(material)
        return materials_found

    def extract_textures_from_shaders(self, material, surface_shader):
        material_name = material.GetPath().name
        # Find the UsdPreviewSurface shader and start traversal from its inputs


        texture_data = []
        if surface_shader:
            # print(f"Found UsdPreviewSurface Shader: {surface_shader=}\n{material_name=}\n{texture_data=}\n\n")
            for input in surface_shader.GetInputs():
                self.traverse_shader_network(surface_shader, material_name, texture_data)
        else:
            print(f"No UsdPreviewSurface Shader found for material: {material_name}")

        return texture_data

    def standardize_textures_format(self, texture_data):
        """standardizes the extracted texture data into my own standardized format for all materials."""
        materials_dict = {}
        for texture in texture_data:
            material_name = texture['material_name']
            # if material_name not in materials_dict:
            #     materials_dict = {
            #         'albedo': '',
            #         'rough': '',
            #         'metallic': '',
            #         'normal': '',
            #         'displacement': '',
            #         'occlusion': ''
            #     }
            connected_input = texture['connected_input']
            file_path = texture['file_path']
            if connected_input == 'diffuseColor':
                materials_dict['albedo'] = file_path
            elif connected_input == 'roughness':
                materials_dict['roughness'] = file_path
            elif connected_input == 'metallic':
                materials_dict['metallness'] = file_path
            elif connected_input == 'normal':
                materials_dict['normal'] = file_path
            elif connected_input == 'occlusion':
                materials_dict['occlusion'] = file_path
        return materials_dict


    def save_textures_to_file(self, texture_data, file_path):
        """Pretty print the texture data dictionary to a text file."""
        with open(file_path, 'w') as file:
            json.dump(texture_data, file, indent=4)
            print(f"Texture data successfully written to {file_path}")


    def save_textures_to_file(self, texture_data, file_path):
        """ Pretty print the texture data dictionary to a text file. """
        with open(file_path, 'w') as file:
            # Pretty print the dictionary with indent
            json.dump(texture_data, file, indent=4)
            print(f"Texture data successfully written to {file_path}")

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


    def create_mat_from_usdpreview_shader_in_stage(self):
        """
        [WIP] this is the main run script, currently in testing phase. works on usdPreviewSurface from SP and the
        ones autocreated from principledshader
        """
        selected_nodes = hou.selectedNodes()

        if not selected_nodes or not isinstance(selected_nodes[0], hou.LopNode):
            raise ValueError("Please select a LOP node.")

        # Get the stage from the selected LOP node
        stage = selected_nodes[0].stage()
        if not stage:
            raise ValueError("Failed to access USD stage from the selected node.")

        classMC = USD_Shaders()
        found_usdpreview_mats = classMC.get_all_usdpreview_mats_from_stage(stage)
        for material in found_usdpreview_mats:
            surface_shader = classMC.find_usd_preview_surface_shader(material)
            textures_dict  = classMC.extract_textures_from_shaders(material, surface_shader)
            # print(f'\n\n{textures_dict=}\n')
            transformed_textures = classMC.standardize_textures_format(textures_dict)
            classMC.save_textures_to_file(transformed_textures, r'F:\Users\Ahmed Hindy\Documents\Adobe\Adobe Substance 3D Painter\export/file.txt')
            # print(f"Extracted Textures: {textures}")  # Debug print
            # classMC.create_principled_shaders_with_textures(textures)

            # following materials_processor stuff needs dicts provided to be PER MATERIAL.
            # I need to make sure all textures are passed to arnold in the end
            mat_context = hou.node('/mat')
            new_dict = materials_processer.Convert._create_usdpreview_shader(mat_context=mat_context, node_name='test_node', textures_dictionary=transformed_textures)
            materials_processer.Convert._connect_usdpreview_textures(usdpreview_nodes_dict=new_dict, textures_dictionary=transformed_textures)


class USDMaterialCreator:
    def __init__(self, stage, material_name, texture_dict):
        self.material_name = material_name
        self.texture_dict = texture_dict
        self.stage = stage

    def create_usd_preview_material(self, parent_path):
        material_path = f'{parent_path}/UsdPreviewMaterial'
        material = UsdShade.Material.Define(self.stage, material_path)

        nodegraph_path = f'{material_path}/UsdPreviewNodeGraph'
        nodegraph = self.stage.DefinePrim(nodegraph_path, 'NodeGraph')

        shader_path = f'{nodegraph_path}/UsdPreviewSurface'
        shader = UsdShade.Shader.Define(self.stage, shader_path)
        shader.CreateIdAttr("UsdPreviewSurface")

        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

        # Create textures for USD Preview Shader
        texture_types_to_inputs = {
            'basecolor': 'diffuseColor',
            'metallic': 'metallic',
            'roughness': 'roughness',
            'normal': 'normal',
            'opacity': 'opacity'
        }

        for tex_type, tex_path in self.texture_dict.items():
            if tex_type in texture_types_to_inputs:
                input_name = texture_types_to_inputs[tex_type]
                texture_prim_path = f'{nodegraph_path}/{tex_type}Texture'
                texture_prim = UsdShade.Shader.Define(self.stage, texture_prim_path)
                texture_prim.CreateIdAttr("UsdUVTexture")
                file_input = texture_prim.CreateInput("file", Sdf.ValueTypeNames.Asset)
                file_input.Set(tex_path)

                # Create Primvar Reader for ST coordinates
                st_reader_path = f'{nodegraph_path}/stReader_{tex_type}'
                st_reader = UsdShade.Shader.Define(self.stage, st_reader_path)
                st_reader.CreateIdAttr("UsdPrimvarReader_float2")
                st_input = st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token)
                st_input.Set("st")
                texture_prim.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_reader.ConnectableAPI(),
                                                                                          "result")

                shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(),
                                                                                          "rgb")

        return material

    def create_arnold_material(self, parent_path):
        shader_path = f'{parent_path}/standard_surface1'
        shader = UsdShade.Shader.Define(self.stage, shader_path)
        shader.CreateIdAttr("arnold:standard_surface")
        material_prim = shader.GetPrim().GetParent()
        material = UsdShade.Material.Define(self.stage, material_prim.GetPath())
        material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(shader.ConnectableAPI(),
                                                                                          "surface")

        # Use the existing method to initialize Arnold shader parameters
        self.initialize_arnold_shader(shader)

        # Create textures for Arnold Shader
        texture_types_to_inputs = {
            'basecolor': 'base_color',
            'metallic': 'metalness',
            'roughness': 'specular_roughness',
            'normal': 'normal',
            'opacity': 'opacity'
        }

        for tex_type, tex_path in self.texture_dict.items():
            if tex_type in texture_types_to_inputs:
                input_name = texture_types_to_inputs[tex_type]
                texture_prim_path = f'{material_prim.GetPath()}/{tex_type}Texture'
                texture_prim = UsdShade.Shader.Define(self.stage, texture_prim_path)
                texture_prim.CreateIdAttr("arnold:image")
                file_input = texture_prim.CreateInput("filename", Sdf.ValueTypeNames.Asset)
                file_input.Set(tex_path)
                shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(),
                                                                                          "rgba")

        return material

    def initialize_arnold_shader(self, shader):
        shader.CreateInput('base', Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput('base_color', Sdf.ValueTypeNames.Float3).Set((0.8, 0.8, 0.8))
        shader.CreateInput('metalness', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('specular', Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput('specular_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('specular_roughness', Sdf.ValueTypeNames.Float).Set(0.2)
        shader.CreateInput('specular_IOR', Sdf.ValueTypeNames.Float).Set(1.5)
        shader.CreateInput('specular_anisotropy', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('specular_rotation', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('coat', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('coat_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('coat_roughness', Sdf.ValueTypeNames.Float).Set(0.1)
        shader.CreateInput('coat_IOR', Sdf.ValueTypeNames.Float).Set(1.5)
        shader.CreateInput('coat_normal', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('coat_affect_color', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('coat_affect_roughness', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('transmission', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('transmission_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('transmission_depth', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('transmission_scatter', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('transmission_scatter_anisotropy', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('transmission_dispersion', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('transmission_extra_roughness', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('subsurface', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('subsurface_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('subsurface_radius', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('subsurface_scale', Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput('subsurface_anisotropy', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('emission', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('emission_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('opacity', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('thin_walled', Sdf.ValueTypeNames.Bool).Set(False)
        shader.CreateInput('sheen', Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput('sheen_color', Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
        shader.CreateInput('sheen_roughness', Sdf.ValueTypeNames.Float).Set(0.3)
        shader.CreateInput('indirect_diffuse', Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput('indirect_specular', Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput('internal_reflections', Sdf.ValueTypeNames.Bool).Set(True)
        shader.CreateInput('caustics', Sdf.ValueTypeNames.Bool).Set(False)
        shader.CreateInput('exit_to_background', Sdf.ValueTypeNames.Bool).Set(False)
        shader.CreateInput('aov_id1', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id2', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id3', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id4', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id5', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id6', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id7', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('aov_id8', Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
        shader.CreateInput('transmit_aovs', Sdf.ValueTypeNames.Bool).Set(False)

    def create_textures(self, stage, material_prim, shader, is_arnold=False):
        texture_types_to_inputs = {
            'basecolor': 'base_color' if is_arnold else 'diffuseColor',
            'metallic': 'metalness' if is_arnold else 'metallic',
            'roughness': 'specular_roughness' if is_arnold else 'roughness',
            'normal': 'normal' if is_arnold else 'normal',
            'opacity': 'opacity'
        }

        for tex_type, tex_path in self.texture_dict.items():
            if tex_type in texture_types_to_inputs:
                input_name = texture_types_to_inputs[tex_type]
                texture_prim_path = f'{material_prim.GetPath()}/{tex_type}Texture'
                texture_prim = UsdShade.Shader.Define(stage, texture_prim_path)
                if is_arnold:
                    texture_prim.CreateIdAttr("arnold:image")
                    file_input = texture_prim.CreateInput("filename", Sdf.ValueTypeNames.Asset)
                    file_input.Set(tex_path)
                    texture_prim.CreateInput("color_space", Sdf.ValueTypeNames.Token).Set("auto")
                    texture_prim.CreateInput("filter", Sdf.ValueTypeNames.Token).Set("smart_bicubic")
                    texture_prim.CreateInput("ignore_missing_textures", Sdf.ValueTypeNames.Bool).Set(False)
                    texture_prim.CreateInput("mipmap_bias", Sdf.ValueTypeNames.Int).Set(0)
                    texture_prim.CreateInput("missing_texture_color", Sdf.ValueTypeNames.Float4).Set((0.0, 0.0, 0.0, 0.0))
                    texture_prim.CreateInput("multiply", Sdf.ValueTypeNames.Float3).Set((1.0, 1.0, 1.0))
                    texture_prim.CreateInput("offset", Sdf.ValueTypeNames.Float3).Set((0.0, 0.0, 0.0))
                    texture_prim.CreateInput("sflip", Sdf.ValueTypeNames.Bool).Set(False)
                    texture_prim.CreateInput("single_channel", Sdf.ValueTypeNames.Bool).Set(False)
                    texture_prim.CreateInput("soffset", Sdf.ValueTypeNames.Float).Set(0.0)
                    texture_prim.CreateInput("sscale", Sdf.ValueTypeNames.Float).Set(1.0)
                    texture_prim.CreateInput("start_channel", Sdf.ValueTypeNames.Int).Set(0)
                    texture_prim.CreateInput("swap_st", Sdf.ValueTypeNames.Bool).Set(False)
                    texture_prim.CreateInput("swrap", Sdf.ValueTypeNames.Token).Set("periodic")
                    texture_prim.CreateInput("tflip", Sdf.ValueTypeNames.Bool).Set(False)
                    texture_prim.CreateInput("toffset", Sdf.ValueTypeNames.Float).Set(0.0)
                    texture_prim.CreateInput("tscale", Sdf.ValueTypeNames.Float).Set(1.0)
                    texture_prim.CreateInput("twrap", Sdf.ValueTypeNames.Token).Set("periodic")
                    texture_prim.CreateInput("uvcoords", Sdf.ValueTypeNames.Float2).Set((0.0, 0.0))
                    shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(), "rgba")
                else:
                    texture_prim.CreateIdAttr("UsdUVTexture")
                    file_input = texture_prim.CreateInput("file", Sdf.ValueTypeNames.Asset)
                    file_input.Set(tex_path)
                    shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(file_input)
            else:
                print(f"Texture type '{tex_type}' not recognized and will be ignored.")

    def create_collect_prim(self):
        collect_path = f'/root/material_py/{self.material_name}_collect'
        collect_material = UsdShade.Material.Define(self.stage, collect_path)
        collect_material.CreateInput("inputenum", Sdf.ValueTypeNames.Int).Set(2)

        # Create the USD Preview Shader under the collect material
        usd_preview_material = self.create_usd_preview_material(collect_path)
        usd_preview_shader = usd_preview_material.GetSurfaceOutput().GetConnectedSource()[0]

        # Create the Arnold Shader under the collect material
        arnold_material = self.create_arnold_material(collect_path)
        arnold_shader = arnold_material.GetOutput("arnold:surface").GetConnectedSource()[0]

        # Connect both shaders to the collect material
        collect_material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(
            arnold_shader, "surface")
        collect_material.CreateOutput("surface", Sdf.ValueTypeNames.Token).ConnectToSource(
            usd_preview_shader, "surface")

        return collect_material.GetPrim()

    @staticmethod
    def run():
        texture_dict = {
            'basecolor': r'f:\My Folder\wallpapers\akin-cakiner-nkUFXi0JSX8-unsplash.jpg',
            # 'metallic': '/path/to/metallic.jpg',
            # 'roughness': '/path/to/roughness.jpg',
            # 'normal': '/path/to/normal.jpg',
            # 'opacity': '/path/to/opacity.jpg'
        }

        node = hou.pwd()
        stage = node.editableStage()

        material_creator = USDMaterialCreator(stage, 'MyMaterial', texture_dict)
        collect_prim = material_creator.create_collect_prim()
        print(f"Collect Material created at: {collect_prim.GetPath()}")

        geo_prim = stage.GetPrimAtPath('/root/Mesh_01_Head/Mesh_01_Head')
        if geo_prim:
            UsdShade.MaterialBindingAPI(geo_prim).Bind(UsdShade.Material(collect_prim))
        else:
            print("Geometry prim not found.")

