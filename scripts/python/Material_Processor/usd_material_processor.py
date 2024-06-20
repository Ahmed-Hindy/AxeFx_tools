"""
Copyright Ahmed Hindy. Please mention the author if you found any part of this code useful.

"""
from importlib import reload
import json
from pprint import pprint
from typing import List, Optional
from pxr import Usd, UsdShade, Sdf

import hou
from Material_Processor.materials_processer import MaterialCreate, TextureInfo, MaterialData
reload(Material_Processor.materials_processer)



class USD_Shaders_Ingest:
    """
    [WIP] this will ingest usd stage, traverse it for all usdPreview materials.
    """

    def __init__(self, stage=None, mat_context=None):
        self.stage = stage or (hou.selectedNodes()[0].stage() if hou.selectedNodes() else None)
        if not self.stage:
            raise ValueError("Please select a LOP node.")

        self.mat_context = mat_context or hou.node('/mat')
        self.all_materials_names = set()
        self.materials_found_in_stage = []

        self.found_usdpreview_mats = None
        self.materialdata_list = []
        self.run()

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

    def _collect_texture_data(self, shader, material_data: MaterialData, path: List[str], connected_param: str):
        """
        Collects texture data from a given shader.
        :param shader: <UsdShade.Shader object> e.g. Usd.Prim(</root/material/_03_Base/UsdPreviewSurface/ShaderUsdPreviewSurface>)
        :param material_data: MaterialData object containing material name and textures
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

        material_data.textures[connected_param] = TextureInfo(
            file_path=file_path,
            traversal_path=' -> '.join(path),
            connected_input=connected_param
        )

        path.pop()

    def _traverse_shader_network(self, shader, material_data: MaterialData, path=None, connected_param="") -> None:
        """
        Main traversal function. Will modify passed 'material'.
        :param shader: <UsdShade.Shader object> e.g. Usd.Prim(</root/material/_03_Base/UsdPreviewSurface/ShaderUsdPreviewSurface>)
        :param material_data: MaterialData object containing material name and textures
        :param path: left empty when run from outside.
        :param connected_param: left empty when run from outside.
        """
        if path is None:
            path = []
        if shader is None:
            return

        self._collect_texture_data(shader, material_data, path, connected_param)

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
                self._traverse_shader_network(connected_shader, material_data, path, connected_param)

    def _find_usd_preview_surface_shader(self, usdshade_material: UsdShade.Material) -> Optional[UsdShade.Shader]:
        """
        :param usdshade_material: UsdShade.Material prim
        :return: UsdShade.Shader prim of type 'UsdPreviewSurface' inside the material if found.
        """
        for shader_output in usdshade_material.GetOutputs():
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
        :return: list of UsdShade.Material of all found material prims in stage.
        """
        for prim in stage.Traverse():
            if not prim.IsA(UsdShade.Material):
                continue
            material = UsdShade.Material(prim)
            self.materials_found_in_stage.append(material)
        return self.materials_found_in_stage

    @staticmethod
    def _get_primitives_assigned_to_material(stage, usdshade_material:  UsdShade.Material, material_data: MaterialData) -> None:
        """
        Adds all primitives that have the given material assigned to them into the material_data.

        :param stage: Usd.Stage object
        :param usdshade_material: UsdShade.Material type primitive on stage
        :param material_data: MaterialData instance containing the material name and textures
        """
        if not isinstance(material_data, MaterialData):
            raise ValueError(f"material_data is not a <MaterialData> object, instead it's a {type(material_data)}.")

        if not usdshade_material or not isinstance(usdshade_material, UsdShade.Material):
            raise ValueError(
                f"Material at path {material_data.material_name} is not a <UsdShade.Material> object, instead it's a {type(usdshade_material)}.")

        material_path = usdshade_material.GetPath()
        bound_prims = []

        for prim in stage.Traverse():
            material_binding_api = UsdShade.MaterialBindingAPI(prim)
            bound_material, _ = material_binding_api.ComputeBoundMaterial()
            if bound_material and bound_material.GetPath() == material_path:
                bound_prims.append(prim)

        material_data.prims_assigned_to_material = bound_prims


    def create_materialdata_object(self, usdshade_material: UsdShade.Material) -> MaterialData:
        """
        Find the UsdPreviewSurface shader and start traversal from its inputs
        :return: MaterialData object with collected texture data
        """
        material_name = usdshade_material.GetPath().name
        material_path = usdshade_material.GetPrim().GetPath().pathString

        self.all_materials_names.add(material_name)
        material_data = MaterialData(usd_material=usdshade_material, material_name=material_name, material_path=material_path)
        return material_data

    def _standardize_textures_format(self, material_data: MaterialData) -> None:
        """
        Standardizes material_data.textures dictionary variable.
        :param material_data: MaterialData object.
        """
        standardized_textures = {}
        for texture_type, texture_info in material_data.textures.items():
            if texture_type == 'diffuseColor':
                standardized_textures['albedo'] = texture_info
            elif texture_type == 'roughness':
                standardized_textures['roughness'] = texture_info
            elif texture_type == 'metallic':
                standardized_textures['metallness'] = texture_info
            elif texture_type == 'normal':
                standardized_textures['normal'] = texture_info
            elif texture_type == 'occlusion':
                standardized_textures['opacity'] = texture_info
            else:
                print(f"Unknown texture type: {texture_type}")

        material_data.textures = standardized_textures

    def _save_textures_to_file(self, materials: List[MaterialData], file_path: str):
        """Pretty print the texture data list to a text file."""
        with open(file_path, 'w') as file:
            json.dump([material.__dict__ for material in materials], file, indent=4, default=lambda o: o.__dict__)
            print(f"Texture data successfully written to {file_path}")

    def run(self):
        """
        ingests usd stage finding all usdPreview materials.
        """
        ## INGESTING:
        self.found_usdpreview_mats = self._get_all_materials_from_stage(self.stage)
        print(f"...{self.found_usdpreview_mats=}\n")
        for usdshade_material in self.found_usdpreview_mats:
            material_data = self.create_materialdata_object(usdshade_material)
            if not material_data:
                print("continuing")
                continue

            usd_preview_surface = self._find_usd_preview_surface_shader(usdshade_material)
            if not usd_preview_surface:
                print(f"WARNING: No UsdPreviewSurface Shader found for material: {material_data.material_name}")
            self._traverse_shader_network(usd_preview_surface, material_data)
            self._standardize_textures_format(material_data)

            USD_Shaders_Ingest._get_primitives_assigned_to_material(self.stage, usdshade_material, material_data)
            print(f"{material_data.usd_material=}")
            self.materialdata_list.append(material_data)


class USD_Shader_Create:
    """
    Creates a collect usd material on stage with Arnold and/or UsdPreview materials. Assigns material to prims
    """
    def __init__(self, stage, material_data: MaterialData,
                 create_usd_preview=True, create_arnold=True):
        self.stage = stage
        self.material_data = material_data
        # if prims_assigned_to_the_mat is None:
        #     prims_assigned_to_the_mat = []
        self.prims_assigned_to_the_mat = material_data.prims_assigned_to_material
        self.create_usd_preview = create_usd_preview
        self.create_arnold = create_arnold
        self.newly_created_usd_mat = None

        self.create_usd_material()

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

        # Fill texture file paths for Arnold Shader
        self._fill_texture_file_paths(material_prim, shader)

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

    def _fill_texture_file_paths(self, material_prim, shader):
        """
        Fills the texture file paths for the given shader using the material_data.
        """
        texture_types_to_inputs = {
            'albedo': 'base_color',
            'metallness': 'metalness',
            'roughness': 'specular_roughness',
            'normal': 'normal',
            'opacity': 'opacity'
        }
        print(f"{self.material_data=}\n\n")
        for tex_type, tex_info in self.material_data.textures.items():
            if tex_type not in texture_types_to_inputs:
                print(f"{tex_type=}")

                continue
            input_name = texture_types_to_inputs[tex_type]
            texture_prim_path = f'{material_prim.GetPath()}/{tex_type}Texture'
            texture_prim = UsdShade.Shader.Define(self.stage, texture_prim_path)
            texture_prim.CreateIdAttr("arnold:image")
            file_input = texture_prim.CreateInput("filename", Sdf.ValueTypeNames.Asset)
            file_input.Set(tex_info.file_path)
            shader.CreateInput(input_name, Sdf.ValueTypeNames.Float3).ConnectToSource(texture_prim.ConnectableAPI(),
                                                                                      "rgba")


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


    def _assign_material_to_primitives(self, new_material: UsdShade.Material) -> None:
        """
        Reassigns a new USD material to a list of primitives.
        :param new_material: UsdShade.Material primitive to assign to the primitives
        """
        if not new_material or not isinstance(new_material, UsdShade.Material):
            raise ValueError(f"New material is not a <UsdShade.Material> object, instead it's a {type(new_material)}.")

        for prim in self.prims_assigned_to_the_mat:
            UsdShade.MaterialBindingAPI(prim).Bind(new_material)


    def create_usd_material(self):
        """
        Main function to run. will create a collect material with Arnold and usdPreview shaders in stage.
        """
        self.newly_created_usd_mat = self._create_collect_prim(parent_prim='/root/material_py/',
                                                               create_usd_preview=self.create_usd_preview,
                                                               create_arnold=self.create_arnold)
        print(f"{self.newly_created_usd_mat=}")
        self._assign_material_to_primitives(self.newly_created_usd_mat)


def ingest_stage_and_recreate_materials(stage):
    """
    [temp] ingests stage, creates new usd materials, and reassign it to prims which already been assigned to previous
     material_data.
    """
    # get all found materials on stage and return a list of MaterialData objects for each one.
    materialdata_list = USD_Shaders_Ingest(stage).materialdata_list

    for material_data in materialdata_list:
        print(f"//{material_data.prims_assigned_to_material=}")
        usd_create = USD_Shader_Create(stage, material_data=material_data)

