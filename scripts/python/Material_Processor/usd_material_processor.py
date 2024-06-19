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

    def __init__(self, stage=None, mat_context=None):
        self.all_materials_names = set()
        self.materials_found_in_stage = []
        if not stage:
            self.selected_nodes = hou.selectedNodes()
            if not self.selected_nodes or not isinstance(self.selected_nodes[0], hou.LopNode):
                raise ValueError("Please select a LOP node.")

            stage = self.selected_nodes[0].stage()
        if not stage:
            raise ValueError("Failed to access USD stage from the selected node.")
        self.stage = stage

        if not mat_context:
            mat_context = hou.node('/mat')
        self.mat_context = mat_context

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


    @staticmethod
    def _get_primitives_assigned_to_material(stage, material: UsdShade.Material) -> List[Usd.Prim]:
        """
        Returns all primitives that have the given material assigned to them.

        :param material: UsdShade.Material primitive on the stage
        :return: List of Usd.Prim objects that have the given material assigned
        """
        if not material and not isinstance(material, UsdShade.Material):
            raise ValueError(f"Material is not a <UsdShade.Material> object, instead it's a {type(UsdShade.Material)}.")

        material_path = material.GetPath()

        bound_prims = []
        for prim in stage.Traverse():
            material_binding_api = UsdShade.MaterialBindingAPI(prim)
            bound_material, _ = material_binding_api.ComputeBoundMaterial()
            if bound_material and bound_material.GetPath() == material_path:
                bound_prims.append(prim)

        # print(f"{material=}, {bound_prims=}\n")
        return bound_prims


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

    def _ingest_usd_stage_material(self, usd_material:UsdShade.Material) -> Optional[MaterialData]:
        """
        given a single usd material prim, will ingest it for texture and parameter data
        :param usd_material: UsdShade.Material prim, e.g. (Usd.Prim(</root/material/_01_Head>))
        :return: MaterialData object with collected texture data.
        """
        if not usd_material:
            print("WARNING: No Material for method _ingest_usd_stage_material()")
            return None
        return self._extract_textures_from_shaders(usd_material)

    def _create_vop_materials(self, mat_context, material_data: MaterialData):
        """
        [temp] create a hou.VopNode shader in a mat net.
        """
        MC = materials_processer.MaterialCreate()
        MC.convert_to_mtlx('principled_test', mat_context, material_data)

    def run(self):
        """
        ingests stage, for every material found will create a material in a mat context
        [NOTE]: we need to get all primitives assigned to that specific material, so we can replace it later
        """
        # INGESTING:
        self.found_usdpreview_mats = self._get_all_materials_from_stage(self.stage)
        print(f"{self.found_usdpreview_mats=}")
        materials_dict = {}
        for usd_material in self.found_usdpreview_mats:
            material_name = usd_material.GetPrim().GetPath().pathString
            prims_assigned_to_material = USD_Shaders_Ingest._get_primitives_assigned_to_material(self.stage, usd_material)

            materials_dict[material_name] = {
                'UsdShade.material': usd_material,
                'assigned_to': prims_assigned_to_material}

            # print('\npprint:')
            # pprint(materials_dict)

            material_data = self._ingest_usd_stage_material(usd_material)
            if not material_data:
                print("continuing")
                continue
            standardized_material_data = self._standardize_textures_format(material_data)


            # CREATION:
            self._create_vop_materials(self.mat_context, standardized_material_data)  # creates VOP material, we need a usd material instead.
            material_creator = USD_Shader_create(self.stage, material_data)
            collect_material_prim = material_creator._create_collect_prim(parent_prim='/root/material_py/',
                                                                          create_usd_preview=True,
                                                                          create_arnold=True)
            # print(f"Collect Material created at: {collect_material_prim}")
            USD_Shader_create._assign_material_to_primitives(prims_assigned_to_material, collect_material_prim)




class USD_Shader_create:
    """
    [WIP] will create USDPreview Material and/ or Arnold material in stage. This class must be run from a python
    LOP node.
    """
    def __init__(self, stage, material_data: MaterialData):
        self.material_data = material_data
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

        for tex_type, tex_info in self.material_data.textures.items():
            if tex_type not in texture_types_to_inputs:
                continue

            input_name = texture_types_to_inputs[tex_type]
            texture_prim_path = f'{nodegraph_path}/{tex_type}Texture'
            texture_prim = UsdShade.Shader.Define(self.stage, texture_prim_path)
            texture_prim.CreateIdAttr("UsdUVTexture")
            file_input = texture_prim.CreateInput("file", Sdf.ValueTypeNames.Asset)
            file_input.Set(tex_info.file_path)

            # Create Primvar Reader for ST coordinates
            st_reader_path = f'{nodegraph_path}/stReader_{tex_type}'
            st_reader = UsdShade.Shader.Define(self.stage, st_reader_path)
            st_reader.CreateIdAttr("UsdPrimvarReader_float2")
            st_input = st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token)
            st_input.Set("st")
            texture_prim.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_reader.ConnectableAPI(), "result")

            shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(), "rgb")

        return material

    def _create_arnold_material(self, parent_path):
        shader_path = f'{parent_path}/standard_surface1'
        shader = UsdShade.Shader.Define(self.stage, shader_path)
        shader.CreateIdAttr("arnold:standard_surface")
        material_prim = shader.GetPrim().GetParent()
        material = UsdShade.Material.Define(self.stage, material_prim.GetPath())
        material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(shader.ConnectableAPI(), "surface")

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

        for tex_type, tex_info in self.material_data.textures.items():
            if tex_type in texture_types_to_inputs:
                input_name = texture_types_to_inputs[tex_type]
                texture_prim_path = f'{material_prim.GetPath()}/{tex_type}Texture'
                texture_prim = UsdShade.Shader.Define(self.stage, texture_prim_path)
                texture_prim.CreateIdAttr("arnold:image")
                file_input = texture_prim.CreateInput("filename", Sdf.ValueTypeNames.Asset)
                file_input.Set(tex_info.file_path)
                shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(), "rgba")

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

    def _create_collect_prim(self, parent_prim='/Scene/materials/', create_usd_preview=True, create_arnold=True) -> UsdShade.Material:
        """
        creates a collect material prim on stage
        :return: UsdShade.Material of the collect prim
        """
        collect_prim_path = f'{parent_prim}{self.material_data.material_name}_collect'
        collect_usd_material = UsdShade.Material.Define(self.stage, collect_prim_path)
        collect_usd_material.CreateInput("inputnum", Sdf.ValueTypeNames.Int).Set(2)

        if create_usd_preview:
            # Create the USD Preview Shader under the collect material
            usd_preview_material = self._create_usd_preview_material(collect_prim_path)
            usd_preview_shader = usd_preview_material.GetSurfaceOutput().GetConnectedSource()[0]
            collect_usd_material.CreateOutput("surface", Sdf.ValueTypeNames.Token).ConnectToSource(usd_preview_shader, "surface")

        if create_arnold:
            # Create the Arnold Shader under the collect material
            arnold_material = self._create_arnold_material(collect_prim_path)
            arnold_shader = arnold_material.GetOutput("arnold:surface").GetConnectedSource()[0]
            collect_usd_material.CreateOutput("arnold:surface", Sdf.ValueTypeNames.Token).ConnectToSource(arnold_shader, "surface")

        return collect_usd_material


    @staticmethod
    def _assign_material_to_primitives(prims: List[Usd.Prim], new_material: UsdShade.Material) -> None:
        """
        Reassigns a new USD material to a list of primitives.

        :param prims: List of Usd.Prim objects that have the old material assigned
        :param new_material: UsdShade.Material primitive to assign to the primitives
        """
        if not new_material or not isinstance(new_material, UsdShade.Material):
            raise ValueError(f"New material is not a <UsdShade.Material> object, instead it's a {type(new_material)}.")

        for prim in prims:
            UsdShade.MaterialBindingAPI(prim).Bind(new_material)
            print(f"Reassigned {prim.GetPath()} to new material {new_material.GetPath()}")


    @staticmethod
    def run(stage, material_data: MaterialData, assign_to_prims: List, create_usd_preview=True, create_arnold=True):
        """
        Main function to run. will create a collect material with Arnold and usdPreview shaders in stage.
        """


        # material_creator = USD_Shader_create(stage, material_data)
        # collect_material_prim = material_creator._create_collect_prim(parent_prim='/root/material_py/',
        #                                                               create_usd_preview=create_usd_preview,
        #                                                               create_arnold=create_arnold)
        # print(f"Collect Material created at: {collect_material_prim}")


        # material_creator._assign_material_to_primitives(assign_to_prims, collect_material_prim)
        return











    # @staticmethod
    # def run(create_usd_preview=True, create_arnold=True):
    #     """
    #     Main function to run. will create a collect material with Arnold and usdPreview shaders in stage.
    #     """
    #     node = hou.pwd()
    #     stage = node.editableStage()
    #     tex_dir = r"F:\Users\Ahmed Hindy\Documents\Adobe\Adobe Substance 3D Painter\export\MeetMat_v001_textures"
    #
    #     material_data = MaterialData(
    #         material_name='MyMaterial',
    #         textures={
    #             'albedo': TextureInfo(file_path=tex_dir + r"\02_Body_Base_color.png", traversal_path='', connected_input=''),
    #             'metallness': TextureInfo(file_path=tex_dir + r"\02_Body_Metallic.png", traversal_path='', connected_input=''),
    #             'roughness': TextureInfo(file_path=tex_dir + r"\02_Body_Roughness.png", traversal_path='', connected_input=''),
    #             'normal': TextureInfo(file_path=tex_dir + r"\02_Body_Normal_DirectX.png", traversal_path='', connected_input=''),
    #             # 'opacity': TextureInfo(file_path='/path/to/opacity.jpg', traversal_path='', connected_input='')
    #         }
    #     )
    #
    #     material_creator = USD_Shader_create(stage, material_data)
    #     collect_prim = material_creator._create_collect_prim(create_usd_preview, create_arnold)
    #     print(f"Collect Material created at: {collect_prim.GetPath()}")
    #
    #     # temp assign to geo
    #     geo_prim = stage.GetPrimAtPath('/root/Mesh_01_Head/Mesh_01_Head')
    #     if geo_prim:
    #         UsdShade.MaterialBindingAPI(geo_prim).Bind(UsdShade.Material(collect_prim))
    #     else:
    #         print("Geometry prim not found.")

