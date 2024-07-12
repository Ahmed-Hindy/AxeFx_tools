"""
copyright Ahmed Hindy. Please mention the original author if you used any part of this code

"""
from typing import Dict, List
from pprint import pprint, pformat
from importlib import reload

try:
    import scripts.python.Material_Processor.material_classes
    reload(scripts.python.Material_Processor.material_classes)
    from scripts.python.Material_Processor.material_classes import TextureInfo, MaterialData, NodeInfo, NodeParameter
except:
    import Material_Processor.material_classes
    reload(Material_Processor.material_classes)
    from Material_Processor.material_classes import TextureInfo, MaterialData, NodeInfo, NodeParameter

try:
    import hou
except:
    hou = None  # temp to make the module work with substance painter


class MaterialIngest:
    def __init__(self, selected_node: hou.node):
        self.old_standard_surface = None
        self.selected_node = selected_node
        if not self.selected_node:
            raise Exception("Please select a node.")

        self.material_name = self.selected_node.name()
        self.material_data = None
        self.shader_parms_dict = None

        self.run()

    @staticmethod
    def get_current_hou_context() -> str:
        current_tab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, 0)
        current_tab_parent = current_tab.pwd()
        print(f"get_current_hou_context()----- {current_tab_parent.type().name()=}")
        return current_tab_parent

    @staticmethod
    def get_texture_nodes_from_all_shader_types(input_node: hou.node) -> Dict[str, hou.VopNode]:
        filtered_dict = {}
        mapped_nodes_dict = {}
        traverse_class = TraverseNodeConnections()
        traverse_tree = traverse_class.traverse_children_nodes(input_node)
        all_connections = traverse_class.map_all_nodes_to_target_input_index(traverse_tree, node_b_type='arnold::standard_surface')
        print(f'\n')
        pprint(traverse_tree)
        print(f'\n')
        standard_surface = [k for k, v in traverse_tree.items() if k.type().name() == 'arnold::standard_surface'][0]
        filtered_dict.update({k: v for k, v in traverse_tree.items() if k.type().name() in ['arnold::image', 'arnold::color_correct', 'arnold::triplanar']})
        mapped_nodes_dict.update(traverse_class.map_connection_input_index_to_texture_type(input_dict=filtered_dict))
        return mapped_nodes_dict

    @staticmethod
    def get_texture_maps_from_parms(input_parms_dict: Dict[str, hou.VopNode]) -> Dict[str, str]:
        textures_dict = {}
        for key, value in input_parms_dict.items():
            if value:
                parm_value = value.parm('filename').unexpandedString()
                textures_dict[key] = parm_value
        print(f'get_texture_maps_from_parms()-----{textures_dict=}\n')
        return textures_dict

    @staticmethod
    def normalize_texture_map_keys(textures_dict: Dict[str, str]) -> Dict[str, str]:
        normalized_dict = {}
        for key, value in textures_dict.items():
            if value:
                if any(k in key for k in ['albedo', 'diffuse', 'basecolor']):
                    normalized_dict['albedo'] = value
                elif any(k in key for k in ['rough', 'roughness']):
                    normalized_dict['roughness'] = value
                elif any(k in key for k in ['metal', 'metallness']):
                    normalized_dict['metallness'] = value
                elif any(k in key for k in ['opacity']):
                    normalized_dict['opacity'] = value
                elif any(k in key for k in ['normal', 'normalmap', 'baseNormal']):
                    normalized_dict['normal'] = value
                elif any(k in key for k in ['dispTex']):
                    normalized_dict['displacement'] = value
                else:
                    print(f"normalize_texture_map_keys()----- a texture_map_key wasn't processed:{key=} is {value=}")
                    normalized_dict[key] = value
        return normalized_dict

    @staticmethod
    def get_shader_parameters_from_arnold_shader(input_node: hou.node) -> Dict:
        """
        Given an Arnold shader node, this function attempts to get all shader parameters like base_color, metalness,
        specular, roughness, etc.
        :return: A normalized dictionary containing shader parameters.
        """
        # print(f'get_shader_parameters_from_arnold_shader()-----{input_node=}')
        shader_parameters_dict = {
            'base': input_node.evalParm('base'),
            'base_color': input_node.parmTuple('base_color').eval(),
            'diffuse_roughness': input_node.evalParm('diffuse_roughness'),
            'metalness': input_node.evalParm('metalness'),
            'specular': input_node.evalParm('specular'),
            'specular_color': input_node.parmTuple('specular_color').eval(),
            'specular_roughness': input_node.evalParm('specular_roughness'),
            'specular_IOR': input_node.evalParm('specular_IOR'),
            'transmission': input_node.evalParm('transmission'),
            'transmission_color': input_node.parmTuple('transmission_color').eval(),
            'subsurface': input_node.evalParm('subsurface'),
            'subsurface_color': input_node.parmTuple('subsurface_color').eval(),
            'emission': input_node.evalParm('emission'),
            'emission_color': input_node.parmTuple('emission_color').eval(),
            'opacity': input_node.parmTuple('opacity').eval(),
        }
        print(f'{shader_parameters_dict=}')
        return shader_parameters_dict

    def get_shader_parameters_from_all_shader_types(self, input_node: hou.node) -> Dict:
        input_shader_parm_dict = {}
        node_type = input_node.type().name()
        if node_type == 'principledshader::2.0':
            input_shader_parm_dict = self.get_shader_parameters_from_principled_shader(input_node)
        elif node_type == 'arnold::standard_surface':
            input_shader_parm_dict = self.get_shader_parameters_from_arnold_shader(input_node)
        elif node_type == 'subnet':  # need a check for mtlx vs usdpreview
            standard_surface_node = [child for child in input_node.children() if child.type().name() == 'mtlxstandard_surface'][0]
            input_shader_parm_dict = self.get_shader_parameters_from_materialx_shader(standard_surface_node)
        else:
            raise Exception(f'Unknown Node Type: {node_type}')

        print(f'//{input_shader_parm_dict=}\n')
        return input_shader_parm_dict

    def run(self):
        input_tex_nodes_dict = self.get_texture_nodes_from_all_shader_types(self.selected_node)

        # Create a dictionary of texture maps
        textures_dict = self.get_texture_maps_from_parms(input_tex_nodes_dict)
        textures_dict_normalized = self.normalize_texture_map_keys(textures_dict)

        # Get shader parameters
        standard_surface_node = \
        [child for child in self.selected_node.children() if child.type().name() == 'arnold::standard_surface'][0]
        self.shader_parms_dict = self.get_shader_parameters_from_all_shader_types(standard_surface_node)

        # Convert dictionaries to MaterialData
        self.material_data = MaterialData(
            material_name=self.selected_node.name(),
            textures={
                key: TextureInfo(
                    file_path=value,
                    nodes=[
                        NodeInfo(
                            node_type=node.type().name(),
                            traversal_path=self.get_traversal_path(node),
                            connected_input_index=str(node.inputs()[0].inputIndex()) if node.inputs() else None
                        ) for node in self.get_traversal_nodes(input_tex_nodes_dict[key])
                    ]
                ) for key, value in textures_dict_normalized.items()
            }
        )

        print(f'\n{self.material_data.textures=}\n\n')




class TraverseNodeConnections:
    def __init__(self) -> None:
        pass

    def traverse_node_tree(self, node: hou.Node, path=None) -> Dict[hou.Node, Dict]:
        if path is None:
            path = []
        node_dict = {node: {}}

        if not node.inputs():
            return node_dict

        for input_node in node.inputs():
            if input_node:
                input_index = next((input.inputIndex() for input in node.inputConnections() if input.inputNode() == input_node), None)
                input_node_dict = self.traverse_node_tree(input_node, path + [node])
                node_dict[node][(input_node, input_index)] = input_node_dict[input_node]

        return node_dict

    def traverse_children_nodes(self, parent_node: hou.Node) -> Dict:
        output_nodes = []
        for child in parent_node.children():
            is_output = not any(child in other_node.inputs() for other_node in parent_node.children())
            if is_output:
                output_nodes.append(child)

        all_branches = {}
        for output_node in output_nodes:
            branch_dict = self.traverse_node_tree(output_node, [])
            all_branches.update(branch_dict)

        print(f'traverse_children_nodes()-----all_branches={all_branches}\n')
        return all_branches

    @staticmethod
    def find_input_index_in_dict(node_dict: Dict, target_node: hou.Node) -> int:
        for key, value in node_dict.items():
            if isinstance(key, tuple) and key[0] == target_node:
                return key[1]
            elif key == target_node:
                return None
            if isinstance(value, dict):
                result = TraverseNodeConnections.find_input_index_in_dict(value, target_node)
                if result is not None:
                    return result
        return None

    @staticmethod
    def get_input_index_to_target_node_type(node_dict: Dict, node_a: hou.Node, node_b_type: str) -> int:
        def flatten_dict(d, flat_dict=None, parent=None):
            if flat_dict is None:
                flat_dict = {}
            for key, value in d.items():
                if isinstance(key, tuple):
                    node, index = key
                    flat_dict[node] = (parent, index)
                    flatten_dict(value, flat_dict, parent=node)
                else:
                    flatten_dict(value, flat_dict, parent=key)
            return flat_dict

        flat_dict = flatten_dict(node_dict)
        current_node = node_a

        while current_node:
            parent_info = flat_dict.get(current_node)
            if parent_info is None:
                break
            parent, index = parent_info
            if parent and parent.type().name() == node_b_type:
                print(f"Connection to {node_b_type} found at index {index}.")
                return index
            current_node = parent

        return None

    @staticmethod
    def map_all_nodes_to_target_input_index(node_dict: Dict, node_b_type='arnold::standard_surface') -> Dict:
        connection_indices = {}

        def iterate_nodes(d):
            for key, value in d.items():
                if isinstance(key, tuple):
                    node, _ = key
                    index = TraverseNodeConnections.get_input_index_to_target_node_type(node_dict, node, node_b_type)
                    connection_indices[node] = index
                    iterate_nodes(value)
                elif isinstance(value, dict):
                    iterate_nodes(value)

        iterate_nodes(node_dict)
        return connection_indices

    @staticmethod
    def find_nodes_of_type(node_dict: Dict, node_type: str, found_nodes=None) -> list:
        if found_nodes is None:
            found_nodes = []

        for key, inputs in node_dict.items():
            node = key[0] if isinstance(key, tuple) else key
            if node and node.type().name() == node_type:
                found_nodes.append(node)
            if isinstance(inputs, dict):
                TraverseNodeConnections.find_nodes_of_type(inputs, node_type, found_nodes)

        return found_nodes

    @staticmethod
    def map_connection_input_index_to_texture_type(input_dict: Dict, renderer='Arnold') -> Dict:
        index_map = {}
        if renderer == 'Arnold':
            index_map = {
                1: 'albedo',
                6: 'roughness',
                10: 'transmission',
                38: 'opacity',
                39: 'normal'
            }

        node_map_dict = {index_map[value]: key for key, value in input_dict.items() if value in index_map}
        return node_map_dict

    @staticmethod
    def update_connected_input_indices(node_dict: Dict, node_info_list: List[NodeInfo]) -> None:
        for node_info in node_info_list:
            node = hou.node(node_info.traversal_path.split(">")[-1])
            index = TraverseNodeConnections.find_input_index_in_dict(node_dict, node)
            node_info.connected_input_index = index

    def create_material_data(self, selected_node: hou.Node) -> MaterialData:
        traverse_tree = self.traverse_children_nodes(selected_node)
        nodes_info = []
        for node in traverse_tree.keys():
            parameters = [NodeParameter(name=parm.name(), value=parm.eval()) for parm in node.parms()]
            traversal_path = ">".join([n.path() for n in traverse_tree.keys()])
            nodes_info.append(NodeInfo(
                node_type=node.type().name(),
                node_name=node.name(),
                parameters=parameters,
                traversal_path=traversal_path,
                connected_input_index=None,
                child_nodes=self._create_child_nodes(node, traverse_tree)
            ))

        material_data = MaterialData(
            material_name=selected_node.name(),
            nodes=nodes_info
        )
        return material_data

    def _create_child_nodes(self, node: hou.Node, traverse_tree: Dict) -> List[NodeInfo]:
        child_nodes = []
        if node in traverse_tree:
            for (child, input_index), grand_children in traverse_tree[node].items():
                parameters = [NodeParameter(name=parm.name(), value=parm.eval()) for parm in child.parms()]
                traversal_path = ">".join([n.path() for n in traverse_tree.keys()])
                child_nodes.append(NodeInfo(
                    node_type=child.type().name(),
                    node_name=child.name(),
                    parameters=parameters,
                    traversal_path=traversal_path,
                    connected_input_index=input_index,
                    child_nodes=self._create_child_nodes(child, grand_children)
                ))
        return child_nodes




class NodeRecreator:
    def __init__(self, material_data: MaterialData, target_context: hou.Node):
        self.material_data = material_data
        self.target_context = target_context
        self.old_new_node_map = {}

    def recreate_nodes(self):
        for node_info in self.material_data.nodes:
            new_node = self._create_node(node_info)
            self.old_new_node_map[node_info.traversal_path] = new_node

        self._set_node_inputs()

    def _create_node(self, node_info: NodeInfo):
        new_node = self.target_context.createNode(node_info.node_type, node_info.node_name)
        for param in node_info.parameters:
            new_node.parm(param.name).set(param.value)
        return new_node

    def _set_node_inputs(self):
        for node_info in self.material_data.nodes:
            new_node = self.old_new_node_map[node_info.traversal_path]
            for child_info in node_info.child_nodes:
                child_node = self.old_new_node_map[child_info.traversal_path]
                new_node.setInput(child_info.connected_input_index, child_node)







class MaterialCreate:
    """
    This class creates material shading networks.
    Input  -> MaterialData with textures and shader attributes.
    Output <- New material shading network.
    Currently, it creates multiple image nodes disregarding the input material.
    """
    def __init__(self, material_data: MaterialData, shader_parms_dict=None, mat_context=hou.node('/mat'), convert_to='arnold'):
        self.material_data = material_data
        self.shader_parms_dict = shader_parms_dict
        self.mat_context = mat_context
        self.convert_to = convert_to

        self.run()



    @staticmethod
    def _create_usdpreview_shader(mat_context: hou.VopNode, node_name: str, material_data: MaterialData) -> Dict:
        """Creates a usdpreview subnet VOP, and inside it creates a usdpreviewsurface and multiple 'usduvtexture::2.0'
           nodes for each EXISTING texture type e.g. 'albedo' or 'roughness' then connects all nodes together.

           :param mat_context: mat library node to create the new usdpreview subnet in.
           :param node_name: name of usdpreview subnet to create, will suffix it with '_usdpreview'.
           :param material_data: MaterialData containing normalized texture names and their paths.
           :return: dict of all created usdpreview nodes
        """

        usdpreview_image_dict = {}

        usdpreview_subnet = mat_context.createNode("subnet", f"{node_name}_usdpreview")
        usd_previewsurface = usdpreview_subnet.createNode("usdpreviewsurface", f"{node_name}_usdpreview")
        usdpreview_image_dict['materialbuilder'] = usdpreview_subnet.path()
        usdpreview_image_dict['standard_surface'] = usd_previewsurface.path()

        primvar_st = usdpreview_subnet.createNode("usdprimvarreader", "usd_primvar_ST")
        primvar_st.parm("signature").set("float2")
        primvar_st.parm("varname").set("st")

        # CREATE ALBEDO
        if 'albedo' in material_data.textures:
            albedo = usdpreview_subnet.createNode("usduvtexture::2.0", "albedo")
            albedo.setInput(1, primvar_st, 0)
            usd_previewsurface.setInput(0, albedo, 4)
            usdpreview_image_dict['image_albedo'] = albedo.path()

        # CREATE ROUGHNESS
        if 'roughness' in material_data.textures:
            roughness = usdpreview_subnet.createNode("usduvtexture::2.0", "roughness")
            usd_previewsurface.setInput(5, roughness, 4)
            roughness.setInput(1, primvar_st, 0)
            usdpreview_image_dict['image_roughness'] = roughness.path()

        usdpreview_subnet.layoutChildren()
        print(f'///{usdpreview_image_dict=}')
        return usdpreview_image_dict

    @staticmethod
    def _connect_usdpreview_textures(usdpreview_nodes_dict: Dict, material_data: MaterialData) -> None:
        """
        Links the texture paths from 'material_data' to the freshly created usdpreviewsurface.
        """
        for texture_type, texture_info in material_data.textures.items():
            if texture_type == 'albedo':
                hou.node(usdpreview_nodes_dict.get('image_albedo')).parm("file").set(texture_info.file_path)
            elif texture_type == 'roughness':
                hou.node(usdpreview_nodes_dict.get('image_roughness')).parm("file").set(texture_info.file_path)
            else:
                print(f'Node {texture_type=} is missing...')

    @staticmethod
    def _apply_shader_parameters_to_usdpreview_shader(new_standard_surface: hou.node, shader_parameters: Dict) -> None:
        """
        Apply shader parameters to a newly created usdpreview shader node.
        :param new_standard_surface: hou.VopNode the newly created usdpreview shader
        :param shader_parameters: A dictionary containing shader parameter values.
        """
        print(f'apply_shader_parameters_to_usdpreview_shader()-----{new_standard_surface=}\n{shader_parameters=}\n')

        new_standard_surface.parmTuple('diffuseColor').set(shader_parameters.get('base_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('metallic').set(shader_parameters.get('metalness', 0.0))
        new_standard_surface.parm('roughness').set(shader_parameters.get('specular_roughness', 0.2))
        new_standard_surface.parm('ior').set(shader_parameters.get('specular_IOR', 1.5))
        new_standard_surface.parmTuple('emissiveColor').set(shader_parameters.get('emission_color', (0.0, 0.0, 0.0)))
        new_standard_surface.parm('opacity').set(shader_parameters.get('opacity', (1,1,1))[0])

        print(f'Shader parameters applied to {new_standard_surface.name()}')

    @staticmethod
    def convert_to_usdpreview(input_mat_node_name, mat_context, material_data: MaterialData, shader_parms_dict=None):
        """Main function to run for creating new usdpreview material"""
        if not material_data:
            raise Exception(f"Cant create a material when {material_data=}")

        usdpreview_nodes_dict = MaterialCreate._create_usdpreview_shader(mat_context, input_mat_node_name,
                                                                         material_data)
        new_standard_surface = hou.node(usdpreview_nodes_dict['standard_surface'])
        MaterialCreate._connect_usdpreview_textures(usdpreview_nodes_dict=usdpreview_nodes_dict,
                                                    material_data=material_data)
        if shader_parms_dict:
            MaterialCreate._apply_shader_parameters_to_usdpreview_shader(new_standard_surface=new_standard_surface,
                                                                         shader_parameters=shader_parms_dict)

        return hou.node(usdpreview_nodes_dict['materialbuilder'])

    @staticmethod
    def _create_mtlx_shader(mat_context: hou.node, node_name: str, material_data: MaterialData) -> Dict:
        """Creates an MTLX subnet VOP, and inside it creates an mtlx standard surface and multiple mtlx image
           nodes for each EXISTING texture type e.g. 'albedo' or 'roughness' then connects all nodes together.

           :param mat_context: mat library node to create the new mtlx subnet in.
           :param node_name: name of mtlx subnet to create, will suffix it with '_materialX'.
           :param material_data: MaterialData containing normalized texture names and their paths.
           :return: dict of all created mtlx nodes
        """
        mtlx_image_dict = {}
        mtlx_subnet = mat_context.createNode("subnet", node_name + "_materialX")
        mtlx_image_dict['materialbuilder'] = mtlx_subnet.path()

        surfaceoutput = mtlx_subnet.createNode("subnetconnector", "surface_output")
        surfaceoutput.parm("parmname").set("surface")
        surfaceoutput.parm("parmlabel").set("Surface")
        surfaceoutput.parm("parmtype").set("surface")
        surfaceoutput.parm("connectorkind").set("output")

        dispoutput = mtlx_subnet.createNode("subnetconnector", "displacement_output")
        dispoutput.parm("parmname").set("displacement")
        dispoutput.parm("parmlabel").set("Displacement")
        dispoutput.parm("parmtype").set("displacement")
        dispoutput.parm("connectorkind").set("output")

        mtlx = mtlx_subnet.createNode("mtlxstandard_surface", "surface_mtlx")
        surfaceoutput.setInput(0, mtlx)
        mtlx_image_dict['standard_surface'] = mtlx.path()

        if 'albedo' in material_data.textures:
            albedo = mtlx_subnet.createNode("mtlximage", "albedo")
            mtlx.setInput(1, albedo)
            mtlx_image_dict['image_albedo'] = albedo.path()

        if 'metallness' in material_data.textures:
            metal = mtlx_subnet.createNode("mtlximage", "metallness")
            metal.parm("signature").set("0")
            mtlx.setInput(3, metal)
            mtlx_image_dict['image_metallness'] = metal.path()

        if 'roughness' in material_data.textures:
            roughness = mtlx_subnet.createNode("mtlximage", "roughness")
            roughness.parm("signature").set("0")
            mtlx.setInput(6, roughness)
            mtlx_image_dict['image_roughness'] = roughness.path()

        if 'opacity' in material_data.textures:
            opacity = mtlx_subnet.createNode("mtlximage", "opacity")
            opacity.parm("signature").set("0")
            opacity.parm("default").set("1")
            mtlx.setInput(38, opacity)
            mtlx_image_dict['image_opacity'] = opacity.path()

        if 'normal' in material_data.textures:
            normal = mtlx_subnet.createNode("mtlximage", "normal")
            normal.parm("signature").set("vector3")
            plugnormal = mtlx_subnet.createNode("mtlxnormalmap")
            mtlx.setInput(40, plugnormal)
            plugnormal.setInput(0, normal)
            mtlx_image_dict['image_normal'] = normal.path()

        if 'displacement' in material_data.textures:
            displacement = mtlx_subnet.createNode("mtlximage", "displacement")
            plugdisplace = mtlx_subnet.createNode("mtlxdisplacement")
            remapdisplace = mtlx_subnet.createNode("mtlxremap", "offset_displace")
            displacement.parm("signature").set("0")
            dispoutput.setInput(0, plugdisplace)
            plugdisplace.setInput(0, remapdisplace)
            remapdisplace.setInput(0, displacement)
            mtlx_image_dict['image_displacement'] = displacement.path()

        mtlx_subnet.layoutChildren()
        return mtlx_image_dict

    @staticmethod
    def _connect_mtlx_textures(mtlx_nodes_dict: Dict, material_data: MaterialData) -> None:
        """
        Links the texture paths from 'material_data' to the freshly created mtlx standard surface.
        """
        for texture_type, texture_info in material_data.textures.items():
            if texture_type == 'albedo':
                hou.node(mtlx_nodes_dict['image_albedo']).parm("file").set(texture_info.file_path)
            elif texture_type == 'roughness':
                hou.node(mtlx_nodes_dict['image_roughness']).parm("file").set(texture_info.file_path)
            elif texture_type == 'metallness':
                hou.node(mtlx_nodes_dict['image_metallness']).parm("file").set(texture_info.file_path)
            elif texture_type == 'opacity':
                hou.node(mtlx_nodes_dict['image_opacity']).parm("file").set(texture_info.file_path)
            elif texture_type == 'normal':
                hou.node(mtlx_nodes_dict['image_normal']).parm("file").set(texture_info.file_path)
            else:
                print(f'mtlx, Node {texture_type=}, is missing...')

    @staticmethod
    def _apply_shader_parameters_to_mtlx_shader(new_standard_surface: hou.node, shader_parameters: Dict) -> None:
        """
        Apply shader parameters to a newly created MaterialX shader node.
        :param new_standard_surface: hou.VopNode the newly created MaterialX shader
        :param shader_parameters: A dictionary containing shader parameter values.
        """
        print(
            f'apply_shader_parameters_to_materialx_shader()-----{new_standard_surface=}\n{shader_parameters=}\n{new_standard_surface.parm("base")=}')

        new_standard_surface.parm('base').set(shader_parameters.get('base', 1.0))
        new_standard_surface.parmTuple('base_color').set(shader_parameters.get('base_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('diffuse_roughness').set(shader_parameters.get('diffuse_roughness', 0.0))
        new_standard_surface.parm('metalness').set(shader_parameters.get('metalness', 0.0))
        new_standard_surface.parm('specular').set(shader_parameters.get('specular', 1.0))
        new_standard_surface.parmTuple('specular_color').set(shader_parameters.get('specular_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('specular_roughness').set(shader_parameters.get('specular_roughness', 0.2))
        new_standard_surface.parm('specular_IOR').set(shader_parameters.get('specular_IOR', 1.5))
        new_standard_surface.parm('transmission').set(shader_parameters.get('transmission', 0.0))
        new_standard_surface.parmTuple('transmission_color').set(
            shader_parameters.get('transmission_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('subsurface').set(shader_parameters.get('subsurface', 0.0))
        new_standard_surface.parmTuple('subsurface_color').set(
            shader_parameters.get('subsurface_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('emission').set(shader_parameters.get('emission', 0.0))
        new_standard_surface.parmTuple('emission_color').set(shader_parameters.get('emission_color', (0.0, 0.0, 0.0)))

        print(f'Shader parameters applied to {new_standard_surface.name()}')

    @staticmethod
    def convert_to_mtlx(input_mat_node_name, mat_context, material_data: MaterialData, shader_parms_dict=None):
        """Main function to run for creating new MTLX material"""
        if not material_data:
            raise Exception(f"Cant create a material when {material_data=}")

        mtlx_nodes_dict = MaterialCreate._create_mtlx_shader(mat_context, input_mat_node_name, material_data)
        new_standard_surface = hou.node(mtlx_nodes_dict['standard_surface'])
        MaterialCreate._connect_mtlx_textures(mtlx_nodes_dict=mtlx_nodes_dict, material_data=material_data)
        if shader_parms_dict:
            MaterialCreate._apply_shader_parameters_to_mtlx_shader(new_standard_surface=new_standard_surface,
                                                                   shader_parameters=shader_parms_dict)

        return hou.node(mtlx_nodes_dict['materialbuilder'])

    @staticmethod
    def _create_principled_shader(mat_context: hou.VopNode, node_name: str, material_data: MaterialData) -> Dict:
        """Creates a principled mat VOP, and links all texture images for each EXISTING texture type e.g. 'albedo' or
           'roughness' then connects all nodes together.

           :param mat_context: mat library node to create the new principled subnet in.
           :param node_name: name of principled subnet to create, will suffix it with '_principled'.
           :param material_data: MaterialData containing normalized texture names and their paths.
           :return: dict of created principled nodes (just one entry)
        """
        principled_shader = mat_context.createNode("principledshader::2.0", node_name + "_principled")

        principled_image_dict = {}
        principled_image_dict['materialbuilder'] = principled_shader.path()

        if 'albedo' in material_data.textures:
            principled_shader.parm('basecolor_useTexture').set(1)

        if 'roughness' in material_data.textures:
            principled_shader.parm('rough_useTexture').set(1)

        if 'metallness' in material_data.textures:
            principled_shader.parm('metallic_useTexture').set(1)

        if 'normal' in material_data.textures:
            principled_shader.parm('baseBumpAndNormal_enable').set(1)

        if 'displacement' in material_data.textures:
            principled_shader.parm('dispTex_enable').set(1)

        return principled_image_dict

    @staticmethod
    def _connect_principled_textures(principled_nodes_dict: Dict, material_data: MaterialData) -> None:
        """
        Links the texture paths from 'material_data' to the freshly created principled shader.
        """
        principled_shader = hou.node(principled_nodes_dict['materialbuilder'])
        for texture_type, texture_info in material_data.textures.items():
            if texture_type == 'albedo':
                principled_shader.parm("basecolor_texture").set(texture_info.file_path)
            elif texture_type == 'roughness':
                principled_shader.parm("rough_texture").set(texture_info.file_path)
            elif texture_type == 'normal':
                principled_shader.parm("baseNormal_texture").set(texture_info.file_path)
            elif texture_type == 'displacement':
                principled_shader.parm("dispTex_texture").set(texture_info.file_path)
            else:
                print(f'Node {texture_type=} is missing...')

    @staticmethod
    def _apply_shader_parameters_to_principled_shader(principled_node: hou.VopNode, shader_parameters: Dict) -> None:
        """
        Apply shader parameters to a newly created principled shader node.
        :param principled_node: hou.VopNode the newly created principled shader
        :param shader_parameters: A dictionary containing shader parameter values.
        """
        print(
            f'apply_shader_parameters_to_principled_shader()-----{principled_node=}\n{shader_parameters=}\n{principled_node.parm("base")=}')

        principled_node.parm('albedomult').set(shader_parameters.get('base', 1.0))
        principled_node.parmTuple('basecolor').set(shader_parameters.get('base_color', (1.0, 1.0, 1.0)))
        principled_node.parm('metallic').set(shader_parameters.get('metalness', 0.0))
        principled_node.parm('reflect').set(shader_parameters.get('specular', 1.0))
        principled_node.parm('rough').set(shader_parameters.get('specular_roughness', 0.2))
        principled_node.parm('ior').set(shader_parameters.get('specular_IOR', 1.5))
        principled_node.parm('transparency').set(shader_parameters.get('transmission', 0.0))
        principled_node.parmTuple('transcolor').set(shader_parameters.get('transmission_color', (1.0, 1.0, 1.0)))
        principled_node.parm('sss').set(shader_parameters.get('subsurface', 0.0))
        principled_node.parmTuple('ssscolor').set(shader_parameters.get('subsurface_color', (1.0, 1.0, 1.0)))
        principled_node.parm('emitint').set(shader_parameters.get('emission', 0.0))
        principled_node.parmTuple('emitcolor').set(shader_parameters.get('emission_color', (0.0, 0.0, 0.0)))

        print(f'Shader parameters applied to {principled_node.name()}')

    @staticmethod
    def convert_to_principled_shader(input_mat_node_name, mat_context, material_data: MaterialData,
                                     shader_parms_dict=None):
        """Main function to run for creating new principled shader material"""
        if not material_data:
            raise Exception(f"Cant create a material when {material_data=}")

        principled_nodes_dict = MaterialCreate._create_principled_shader(mat_context, input_mat_node_name,
                                                                         material_data)
        principled_shader = hou.node(principled_nodes_dict['materialbuilder'])
        MaterialCreate._connect_principled_textures(principled_nodes_dict=principled_nodes_dict,
                                                    material_data=material_data)
        if shader_parms_dict:
            MaterialCreate._apply_shader_parameters_to_principled_shader(principled_node=principled_shader,
                                                                         shader_parameters=shader_parms_dict)

        return hou.node(principled_nodes_dict['materialbuilder'])

    @staticmethod
    def _create_arnold_shader(mat_context: hou.node, node_name: str, material_data: MaterialData) -> Dict:
        arnold_image_dict = {}
        arnold_builder = mat_context.createNode("arnold_materialbuilder", node_name + "_arnold")
        arnold_image_dict['materialbuilder'] = arnold_builder.path()

        output_node = arnold_builder.node('OUT_material')
        node_std_surface = arnold_builder.createNode("arnold::standard_surface")
        output_node.setInput(0, node_std_surface)
        arnold_image_dict['standard_surface'] = node_std_surface.path()

        for texture_type, texture_info in material_data.textures.items():
            current_node = None
            for node_info in texture_info.nodes:
                if node_info.node_type == 'arnold::image':
                    image_node = arnold_builder.createNode("arnold::image", texture_type)
                    image_node.parm("filename").set(texture_info.file_path)
                    current_node = image_node
                    arnold_image_dict[f'image_{texture_type}'] = image_node.path()
                else:
                    node = arnold_builder.createNode(node_info.node_type)
                    node.setInput(0, current_node)
                    current_node = node
                    arnold_image_dict[f'{node_info.node_type}_{texture_type}'] = node.path()
            print(f"{texture_info.nodes[-1]=}")
            node_std_surface.setInput(int(texture_info.nodes[-1].connected_input_index), current_node)

        arnold_builder.layoutChildren()
        return arnold_image_dict

    @staticmethod
    def _connect_arnold_textures(arnold_nodes_dict: Dict, material_data: MaterialData) -> None:
        print(f'{arnold_nodes_dict=}\n')
        for texture_type, texture_info in material_data.textures.items():
            image_node = hou.node(arnold_nodes_dict[f'image_{texture_type}'])
            image_node.parm("filename").set(texture_info.file_path)
            for node_info in texture_info.nodes:
                if node_info.node_type != 'arnold::image':
                    node = hou.node(arnold_nodes_dict[f'{node_info.node_type}_{texture_type}'])
                    node.setInput(0, image_node)

    @staticmethod
    def _connect_arnold_textures(arnold_nodes_dict: Dict, material_data: MaterialData) -> None:
        print(f'{arnold_nodes_dict=}\n')
        for texture_type, texture_info in material_data.textures.items():
            image_node = hou.node(arnold_nodes_dict[f'image_{texture_type}'])
            image_node.parm("filename").set(texture_info.file_path)
            for node_info in texture_info.nodes:
                if node_info.node_type != 'arnold::image':
                    node = hou.node(arnold_nodes_dict[f'{node_info.node_type}_{texture_type}'])
                    node.setInput(0, image_node)

    @staticmethod
    def _apply_shader_parameters_to_arnold_shader(new_standard_surface: hou.node, shader_parameters: Dict) -> None:
        """
        Apply shader parameters to a newly created Arnold shader node.
        """
        new_standard_surface.parm('base').set(shader_parameters.get('base'))
        new_standard_surface.parmTuple('base_color').set(shader_parameters.get('base_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('diffuse_roughness').set(shader_parameters.get('diffuse_roughness', 0.0))
        new_standard_surface.parm('metalness').set(shader_parameters.get('metalness', 0.0))
        new_standard_surface.parm('specular').set(shader_parameters.get('specular', 1.0))
        new_standard_surface.parmTuple('specular_color').set(shader_parameters.get('specular_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('specular_roughness').set(shader_parameters.get('specular_roughness', 0.2))
        new_standard_surface.parm('specular_IOR').set(shader_parameters.get('specular_IOR', 1.5))
        new_standard_surface.parm('transmission').set(shader_parameters.get('transmission', 0.0))
        new_standard_surface.parmTuple('transmission_color').set(
            shader_parameters.get('transmission_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('subsurface').set(shader_parameters.get('subsurface', 0.0))
        new_standard_surface.parmTuple('subsurface_color').set(
            shader_parameters.get('subsurface_color', (1.0, 1.0, 1.0)))
        new_standard_surface.parm('emission').set(shader_parameters.get('emission', 0.0))
        new_standard_surface.parmTuple('emission_color').set(shader_parameters.get('emission_color', (0.0, 0.0, 0.0)))

        print(f'Shader parameters applied to {new_standard_surface.name()}')

    @staticmethod
    def convert_to_arnold(input_mat_node_name, mat_context, material_data: MaterialData, shader_parms_dict=None):
        """Main function to run for creating new Arnold material"""
        if not material_data:
            raise Exception(f"Cant create a material when {material_data=}")

        arnold_nodes_dict = MaterialCreate._create_arnold_shader(mat_context, input_mat_node_name, material_data)
        new_standard_surface = hou.node(arnold_nodes_dict['standard_surface'])
        MaterialCreate._connect_arnold_textures(arnold_nodes_dict=arnold_nodes_dict, material_data=material_data)
        if shader_parms_dict:
            MaterialCreate._apply_shader_parameters_to_arnold_shader(new_standard_surface=new_standard_surface,
                                                                     shader_parameters=shader_parms_dict)

        return hou.node(arnold_nodes_dict['materialbuilder'])

    def run(self):
        """
        Main function to run, creates Principledshader, usdpreview, Arnold, and MTLX textures.
        """
        # Convert to the specified shader type
        old_mat_name = self.material_data.material_name
        if self.convert_to == 'principled_shader':
            new_shader = MaterialCreate.convert_to_principled_shader(old_mat_name, self.mat_context, self.material_data,
                                                                     self.shader_parms_dict)
        elif self.convert_to == 'mtlx':
            new_shader = MaterialCreate.convert_to_mtlx(old_mat_name, self.mat_context, self.material_data,
                                                        self.shader_parms_dict)
        elif self.convert_to == 'arnold':
            new_shader = MaterialCreate.convert_to_arnold(old_mat_name, self.mat_context, self.material_data,
                                                          self.shader_parms_dict)
        elif self.convert_to == 'usdpreview':
            new_shader = MaterialCreate.convert_to_usdpreview(old_mat_name, self.mat_context, self.material_data,
                                                              self.shader_parms_dict)
        else:
            raise Exception(f"Wrong format to convert to: {self.convert_to}")

        new_shader.moveToGoodPosition(move_unconnected=False)



