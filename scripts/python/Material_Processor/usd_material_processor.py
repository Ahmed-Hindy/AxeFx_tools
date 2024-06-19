"""
Copyright Ahmed Hindy. Please mention the author if you found any part of this code useful.

"""
from importlib import reload
import json
from pprint import pprint, pformat
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

try:
    import hou
    from Material_Processor import materials_processer  # why do we have to do this in Houdini if they both exist in the same directory!!!
except:
    import materials_processer

reload(materials_processer)
from pxr import Usd, UsdShade, Sdf




@dataclass
class TextureInfo:
    file_path: str
    traversal_path: str
    connected_input: Optional[str] = None

    def __str__(self):
        return f"TextureInfo(file_path={self.file_path}, traversal_path={self.traversal_path}, connected_input={self.connected_input})"


@dataclass
class MaterialData:
    material_name: str
    textures: Dict[str, TextureInfo] = field(default_factory=dict)

    def __str__(self):
        return self._pretty_print()

    def __repr__(self):
        return self._pretty_print()

    def _pretty_print(self):
        data_dict = asdict(self)
        return pformat(data_dict, indent=4)


class USD_Shaders_Ingest:
    """
    [WIP] this will ingest usd stage, traverse it for all usdPreview materials.
    """

    def __init__(self):
        self.all_materials_names = set()
        self.materials_found_in_stage = []
        self.selected_nodes = hou.selectedNodes()
        if not self.selected_nodes or not isinstance(self.selected_nodes[0], hou.LopNode):
            raise ValueError("Please select a LOP node.")

        self.stage = self.selected_nodes[0].stage()
        if not self.stage:
            raise ValueError("Failed to access USD stage from the selected node.")

        self.mat_context = hou.node('/mat')
        if not self.mat_context:
            raise ValueError("Mat Context doesn't exist.")

    def _get_connected_file_path(self, shader_input):
        """
        Recursively follow shader input connections to find the actual file path.
        :param shader_input: <pxr.UsdShade.Input object>. which we get from <UsdShade.Shader object>.GetInput('file')
        """
        connection = shader_input.GetConnectedSource()
        while connection:
            connected_shader_api, connected_input_name, _ = connection
            connected_shader = UsdShade.Shader(connected_shader_api.GetPrim())
            connected_input = connected_shader.GetInput(connected_input_name)

            if connected_input and connected_input.HasConnectedSource():
                connection = connected_input.GetConnectedSource()
            else:
                return connected_input.Get()

    def _collect_texture_data(self, shader, material: MaterialData, path: List[str], connected_param: str):
        """
        Collects texture data from a given shader.
        :param shader: <UsdShade.Shader object> e.g. Usd.Prim(</root/material/_03_Base/UsdPreviewSurface/ShaderUsdPreviewSurface>)
        :param material: MaterialData object containing material name and textures
        :param path: list representing the traversal path.
        :param connected_param: connected parameter name.
        """
        shader_prim = shader.GetPrim()
        shader_info_id = shader_prim.GetAttribute('info:id').Get()
        path.append(shader_info_id or shader_prim.GetName())

        if shader_info_id != 'UsdUVTexture':
            path.pop()
            return

        file_path_attr = shader.GetInput('file')
        if not file_path_attr or not isinstance(file_path_attr, UsdShade.Input):
            print(f'File path attribute is not found or not connected for {shader_prim}')
            path.pop()
            return

        attr_value = file_path_attr.Get() or self._get_connected_file_path(file_path_attr)
        if not isinstance(attr_value, Sdf.AssetPath):
            print(f'Invalid asset path type: {type(attr_value)}')
            path.pop()
            return

        file_path = attr_value.resolvedPath or attr_value.path
        if not file_path:
            print(f'Empty file path for asset: {attr_value}')
            path.pop()
            return

        material.textures[connected_param] = TextureInfo(
            file_path=file_path,
            traversal_path=' -> '.join(path),
            connected_input=connected_param
        )

        path.pop()

    def _traverse_shader_network(self, shader, material: MaterialData, path=None, connected_param="") -> None:
        """
        Main traversal function. Will modify passed 'material'.
        :param shader: <UsdShade.Shader object> e.g. Usd.Prim(</root/material/_03_Base/UsdPreviewSurface/ShaderUsdPreviewSurface>)
        :param material: MaterialData object containing material name and textures
        :param path: left empty when run from outside.
        :param connected_param: left empty when run from outside.
        """
        if path is None:
            path = []
        if shader is None:
            return

        self._collect_texture_data(shader, material, path, connected_param)

        shader_prim = shader.GetPrim()
        shader_id = shader_prim.GetAttribute('info:id').Get()

        # Recursive traversal for UsdPreviewSurface
        for input in shader.GetInputs():
            connection_info = input.GetConnectedSource()
            if connection_info:
                connected_shader_api, source_name, _ = connection_info
                connected_shader = UsdShade.Shader(connected_shader_api.GetPrim())

                # If it's connected to a UsdPreviewSurface, track the input name
                if shader_id == 'UsdPreviewSurface':
                    connected_param = input.GetBaseName()

                # Call the method recursively
                self._traverse_shader_network(connected_shader, material, path, connected_param)

    def _find_usd_preview_surface_shader(self, material) -> Optional[UsdShade.Shader]:
        """
        :param material: usd material prim
        :return: UsdShade.Shader prim of type 'UsdPreviewSurface' inside the material if found.
        """
        for shader_output in material.GetOutputs():
            connection = shader_output.GetConnectedSource()
            if not connection:
                continue
            connected_shader_api, _, _ = connection
            connected_shader = UsdShade.Shader(connected_shader_api.GetPrim())
            shader_id = connected_shader.GetPrim().GetAttribute('info:id').Get()
            if shader_id == 'UsdPreviewSurface':
                return connected_shader
        return None

    def _get_all_materials_from_stage(self, stage) -> List[UsdShade.Material]:
        """
        :param stage: Usd.Stage object
        :return: a list of all found material prims in stage.
        """
        for prim in stage.Traverse():
            if not prim.IsA(UsdShade.Material):
                continue
            material = UsdShade.Material(prim)
            self.materials_found_in_stage.append(material)
        return self.materials_found_in_stage

    def _extract_textures_from_shaders(self, material) -> MaterialData:
        """
        Find the UsdPreviewSurface shader and start traversal from its inputs
        :return: MaterialData object with collected texture data
        """
        material_name = material.GetPath().name
        self.all_materials_names.add(material_name)
        material_data = MaterialData(material_name=material_name)
        surface_shader = self._find_usd_preview_surface_shader(material)
        if not surface_shader:
            print(f"WARNING: No UsdPreviewSurface Shader found for material: {material_name}")
        self._traverse_shader_network(surface_shader, material_data)
        return material_data

    def _standardize_textures_format(self, material: MaterialData) -> MaterialData:
        """
        Standardizes the extracted texture data into my own standardized format for all materials.
        :param materials: List of MaterialData objects containing material name and textures.
        """
        standardized_materials = []
        standardized_material = MaterialData(material_name=material.material_name)

        for texture_type, texture_info in material.textures.items():
            if texture_type == 'diffuseColor':
                standardized_material.textures['albedo'] = texture_info
            elif texture_type == 'roughness':
                standardized_material.textures['roughness'] = texture_info
            elif texture_type == 'metallic':
                standardized_material.textures['metallness'] = texture_info
            elif texture_type == 'normal':
                standardized_material.textures['normal'] = texture_info
            elif texture_type == 'occlusion':
                standardized_material.textures['opacity'] = texture_info
            else:
                print(f"Unknown texture type: {texture_type}")

        # standardized_materials.append(standardized_material)
        return standardized_material

    def _save_textures_to_file(self, materials: List[MaterialData], file_path: str):
        """Pretty print the texture data list to a text file."""
        with open(file_path, 'w') as file:
            json.dump([material.__dict__ for material in materials], file, indent=4, default=lambda o: o.__dict__)
            print(f"Texture data successfully written to {file_path}")

    def _ingest_usd_stage_material(self, material) -> Optional[MaterialData]:
        """
        given a single usd material prim, will ingest it for texture and parameter data
        :param material: UsdShade.Material prim, e.g. (Usd.Prim(</root/material/_01_Head>))
        :return: MaterialData object with collected texture data.
        """
        if not material:
            print("WARNING: No Material for method _ingest_usd_stage_material()")
            return None
        return self._extract_textures_from_shaders(material)

    def _create_materials_from_textures(self, mat_context, material: MaterialData):
        """
        [temp] create a hou.VopNode shader in a mat net.
        """
        MC = materials_processer.MaterialCreate()
        MC.convert_to_mtlx('principled_test', mat_context, material)

    def run(self):
        """
        ingests stage, for every material found will create a material in a mat context
        """
        self.found_usdpreview_mats = self._get_all_materials_from_stage(self.stage)
        materials = []
        for material in self.found_usdpreview_mats:
            if material_data := self._ingest_usd_stage_material(material):
                standardized_materials = self._standardize_textures_format(material_data)

                materials.append(standardized_materials)
                # print(f"{standardized_materials=}\n")
        for material in materials:
            self._create_materials_from_textures(self.mat_context, material)


class USD_Shader_create:
    """
    [WIP] will create USDPreview Material and/ or Arnold material  in stage. this class must be run from a python
    LOP node.
    """
    def __init__(self, stage, material_name, texture_dict):
        self.material_name = material_name
        self.texture_dict = texture_dict
        self.stage = stage

    def _create_usd_preview_material(self, parent_path):
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
            'albedo': 'diffuseColor',
            'metallness': 'metallic',
            'roughness': 'roughness',
            'normal': 'normal',
            'opacity': 'opacity'
        }
        # print(f"{self.texture_dict=}")
        for tex_type, tex_path in self.texture_dict.items():
            if tex_type not in texture_types_to_inputs:
                continue

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

    def _create_arnold_material(self, parent_path):
        shader_path = f'{parent_path}/standard_surface1'
        shader = UsdShade.Shader.Define(self.stage, shader_path)
        shader.CreateIdAttr("arnold:standard_surface")
        material_prim = shader.GetPrim().GetParent()
        material = UsdShade.Material.Define(self.stage, material_prim.GetPath())
        material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(shader.ConnectableAPI(),
                                                                                          "surface")

        # Use the existing method to initialize Arnold shader parameters
        self._initialize_arnold_shader(shader)

        # Create textures for Arnold Shader
        texture_types_to_inputs = {
            'albedo': 'base_color',
            'metallness': 'metalness',
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

    def _initialize_arnold_shader(self, shader):
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

    def _create_textures(self, stage, material_prim, shader, is_arnold=False):
        texture_types_to_inputs = {
            'albedo': 'base_color' if is_arnold else 'diffuseColor',
            'metallness': 'metalness' if is_arnold else 'metallic',
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

    def _create_collect_prim(self, create_usd_preview=True, create_arnold=True):
        collect_path = f'/root/material_py/{self.material_name}_collect'
        collect_material = UsdShade.Material.Define(self.stage, collect_path)
        collect_material.CreateInput("inputnum", Sdf.ValueTypeNames.Int).Set(2)

        if create_usd_preview:
            # Create the USD Preview Shader under the collect material
            usd_preview_material = self._create_usd_preview_material(collect_path)
            usd_preview_shader = usd_preview_material.GetSurfaceOutput().GetConnectedSource()[0]
            collect_material.CreateOutput("surface", Sdf.ValueTypeNames.Token).ConnectToSource(
                usd_preview_shader, "surface")

        if create_arnold:
            # Create the Arnold Shader under the collect material
            arnold_material = self._create_arnold_material(collect_path)
            arnold_shader = arnold_material.GetOutput("arnold:surface").GetConnectedSource()[0]
            collect_material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(
                arnold_shader, "surface")

        return collect_material.GetPrim()

    @staticmethod
    def run(create_usd_preview=True, create_arnold=True):
        """
        Main function to run. will create a collect material with Arnold and usdPreview shaders in stage.
        """
        tex_dir = r"F:\Users\Ahmed Hindy\Documents\Adobe\Adobe Substance 3D Painter\export\MeetMat_textures"
        texture_dict = {
            'albedo': tex_dir + r"\02_Body_Base_color.png",
            'metallness': tex_dir + r"\02_Body_Metallic.png",
            'roughness': tex_dir + r"\02_Body_Roughness.png",
            'normal': tex_dir + r"\02_Body_Normal_DirectX.png",
            # 'opacity': '/path/to/opacity.jpg'
        }

        node = hou.pwd()
        stage = node.editableStage()

        # create_usd_preview = False ###
        material_creator = USD_Shader_create(stage, 'MyMaterial', texture_dict)
        collect_prim = material_creator._create_collect_prim(create_usd_preview, create_arnold)
        print(f"Collect Material created at: {collect_prim.GetPath()}")

        # temp assign to geo
        geo_prim = stage.GetPrimAtPath('/root/Mesh_01_Head/Mesh_01_Head')
        if geo_prim:
            UsdShade.MaterialBindingAPI(geo_prim).Bind(UsdShade.Material(collect_prim))
        else:
            print("Geometry prim not found.")

