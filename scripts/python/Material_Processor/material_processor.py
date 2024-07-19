"""
copyright Ahmed Hindy. Please mention the original author if you used any part of this code
This module processes material nodes in Houdini, extracting and converting shader parameters and textures.


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



class TraverseNodeConnections:
    """
    A class to traverse node connections in Houdini.

    Methods:
        traverse_node_tree(node, path=None): Traverses the node tree and returns a dictionary of nodes.
        traverse_children_nodes(parent_node): Traverses child nodes and returns a dictionary of all branches.
        find_input_index_in_dict(node_dict, target_node): Finds the input index in a dictionary.
        get_input_index_to_target_node_type(node_dict, node_a, node_b_type): Gets the input index to the target node type.
        map_all_nodes_to_target_input_index(node_dict, node_b_type='arnold::standard_surface'): Maps all nodes to the target input index.
        find_nodes_of_type(node_dict, node_type, found_nodes=None): Finds nodes of a specific type.
        map_connection_input_index_to_texture_type(input_dict, renderer='Arnold'): Maps connection input index to texture type.
        update_connected_input_indices(node_dict, node_info_list): Updates connected input indices.
        filter_node_parameters(node): Filters node parameters based on node type and renderer.
        create_material_data(selected_node): Creates material data from the selected node.
    """
    def __init__(self) -> None:
        pass

    STANDARDIZED_PARAM_NAMES = {
        'mtlxstandard_surface': {
            'base': 'base',
            'base_colorr': 'base_colorr',
            'base_colorg': 'base_colorg',
            'base_colorb': 'base_colorb',
            'diffuse_roughness': 'diffuse_roughness',
            'metalness': 'metalness',
            'specular': 'specular',
            'specular_colorr': 'specular_colorr',
            'specular_colorg': 'specular_colorg',
            'specular_colorb': 'specular_colorb',
            'specular_roughness': 'specular_roughness',
            'specular_IOR': 'specular_IOR',
            'transmission': 'transmission',
            'transmission_colorr': 'transmission_colorr',
            'transmission_colorg': 'transmission_colorg',
            'transmission_colorb': 'transmission_colorb',
            'subsurface': 'subsurface',
            'subsurface_color': 'subsurface_color',
            'emission': 'emission',
            'emission_colorr': 'emission_colorr',
            'emission_colorg': 'emission_colorg',
            'emission_colorb': 'emission_colorb',
            'opacity': 'opacity'
        },
        'mtlximage': {
            'file': 'filename'
        },


        'arnold::standard_surface': {
            'base': 'base',
            'base_colorr': 'base_colorr',
            'base_colorg': 'base_colorg',
            'base_colorb': 'base_colorb',
            'diffuse_roughness': 'diffuse_roughness',
            'metalness': 'metalness',
            'specular': 'specular',
            'specular_colorr': 'specular_colorr',
            'specular_colorg': 'specular_colorg',
            'specular_colorb': 'specular_colorb',
            'specular_roughness': 'specular_roughness',
            'specular_IOR': 'specular_IOR',
            'transmission': 'transmission',
            'transmission_colorr': 'transmission_colorr',
            'transmission_colorg': 'transmission_colorg',
            'transmission_colorb': 'transmission_colorb',
            'subsurface': 'subsurface',
            'subsurface_color': 'subsurface_color',
            'emission': 'emission',
            'emission_colorr': 'emission_colorr',
            'emission_colorg': 'emission_colorg',
            'emission_colorb': 'emission_colorb',
            'opacity': 'opacity'
        },
        'arnold::image': {
            'filename': 'filename'
        },
        # Add dictionaries for other node types as needed
    }


    def traverse_node_tree(self, node: hou.Node, path=None) -> Dict[hou.Node, Dict]:
        """
        Traverses the node tree and returns a dictionary of nodes.

        Args:
            node (hou.Node): The input Houdini node.
            path (list): The path of nodes.

        Returns:
            Dict[hou.Node, Dict]: A dictionary of nodes.
        """
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
        """
        Traverses child nodes and returns a dictionary of all branches.

        Args:
            parent_node (hou.Node): The parent Houdini node.

        Returns:
            Dict: A dictionary of all branches.
        """
        output_nodes = []
        for child in parent_node.children():
            is_output = not any(child in other_node.inputs() for other_node in parent_node.children())
            if is_output:
                output_nodes.append(child)

        all_branches = {}
        for output_node in output_nodes:
            branch_dict = self.traverse_node_tree(output_node, [])
            all_branches.update(branch_dict)

        print('traverse_children_nodes()-----all_branches:')
        pprint(all_branches, indent=3)
        print(f'\n')
        return all_branches

    @staticmethod
    def find_input_index_in_dict(node_dict: Dict, target_node: hou.Node) -> int:
        """
        Finds the input index in a dictionary.

        Args:
            node_dict (Dict): The node dictionary.
            target_node (hou.Node): The target Houdini node.

        Returns:
            int: The input index.
        """
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
        """
        Gets the input index to the target node type.

        Args:
            node_dict (Dict): The node dictionary.
            node_a (hou.Node): The starting Houdini node.
            node_b_type (str): The target node type.

        Returns:
            int: The input index to the target node type.
        """
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
        """
        Maps all nodes to the target input index.

        Args:
            node_dict (Dict): The node dictionary.
            node_b_type (str): The target node type.

        Returns:
            Dict: A dictionary mapping nodes to the target input index.
        """
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
        """
        Finds nodes of a specific type.

        Args:
            node_dict (Dict): The node dictionary.
            node_type (str): The node type to find.
            found_nodes (list): A list to store found nodes.

        Returns:
            list: A list of nodes of the specified type.
        """
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
        """
        Maps connection input index to texture type.

        Args:
            input_dict (Dict): The input dictionary.
            renderer (str): The renderer type.

        Returns:
            Dict: A dictionary mapping connection input index to texture type.
        """
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
        """
        Updates connected input indices.

        Args:
            node_dict (Dict): The node dictionary.
            node_info_list (List[NodeInfo]): A list of NodeInfo objects.
        """
        for node_info in node_info_list:
            node = hou.node(node_info.traversal_path.split(">")[-1])
            index = TraverseNodeConnections.find_input_index_in_dict(node_dict, node)
            node_info.connected_input_index = index

    def filter_node_parameters(self, node: hou.Node) -> List[NodeParameter]:
        """
        Filters node parameters based on node type and standardizes their names.

        Args:
            node (hou.Node): The Houdini node.

        Returns:
            List[NodeParameter]: A list of filtered and standardized node parameters.
        """
        node_type = node.type().name()
        param_names = []
        standardized_names = self.STANDARDIZED_PARAM_NAMES.get(node_type, {})

        if node_type in ['mtlxstandard_surface', 'arnold::standard_surface']:
            param_names = [
                'base', 'base_colorr', 'base_colorg', 'base_colorb', 'diffuse_roughness', 'metalness', 'specular',
                'specular_colorr', 'specular_colorg', 'specular_colorb', 'specular_roughness', 'specular_IOR',
                'transmission', 'transmission_colorr', 'transmission_colorg', 'transmission_colorb', 'subsurface',
                'subsurface_color', 'emission', 'emission_colorr', 'emission_colorg', 'emission_colorb', 'opacity'
            ]
        elif node_type in ['mtlximage', 'arnold::image']:
            param_names = ['file']

        node_parameters = [
            NodeParameter(name=p.name(), value=p.eval(),
                          standardized_name=standardized_names.get(p.name(), p.name()))
            for p in node.parms() if p.name() in param_names
        ]
        return node_parameters

    def _create_child_nodes(self, node: hou.Node, traverse_tree: Dict) -> List[NodeInfo]:
        """
        Creates child nodes from the traversal tree.

        Args:
            node (hou.Node): The Houdini node.
            traverse_tree (Dict): The traversal tree.

        Returns:
            List[NodeInfo]: A list of child NodeInfo objects.
        """
        child_nodes = []
        if node in traverse_tree:
            for (child, input_index), grand_children in traverse_tree[node].items():
                parameters = self.filter_node_parameters(child)
                traversal_path = child.path()
                print(f"Creating child NodeInfo for node: {child.path()} with parameters: {parameters}")
                child_nodes.append(NodeInfo(
                    node_type=child.type().name(),
                    node_name=child.name(),
                    parameters=parameters,
                    traversal_path=traversal_path,
                    connected_input_index=input_index,
                    child_nodes=self._create_child_nodes(child, grand_children)
                ))
        print(f"Child Nodes for {node.path()}: {child_nodes}")
        return child_nodes

    def create_material_data(self, selected_node: hou.Node) -> MaterialData:
        """
        Creates material data from the selected node.

        Args:
            selected_node (hou.Node): The selected Houdini node.

        Returns:
            MaterialData: The created material data.
        """
        traverse_tree = self.traverse_children_nodes(selected_node)
        nodes_info = []

        def traverse_and_create_node_info(node_dict: Dict, parent_node: hou.Node = None):
            local_nodes_info = []
            for key, children in node_dict.items():
                # Handle key being a tuple (node, index) or just a node
                if isinstance(key, tuple):
                    node = key[0]
                    connected_input_index = key[1]
                else:
                    node = key
                    connected_input_index = None

                parameters = self.filter_node_parameters(node)
                traversal_path = node.path()
                # print(f"Creating NodeInfo for node: {traversal_path} with parameters: {parameters}")

                # Create NodeInfo for the current node
                node_info = NodeInfo(
                    node_type=node.type().name(),
                    node_name=node.name(),
                    parameters=parameters,
                    traversal_path=traversal_path,
                    connected_input_index=connected_input_index,
                    child_nodes=[]
                )

                # Recursively process child nodes
                child_nodes_info = traverse_and_create_node_info(children, node)
                node_info.child_nodes.extend(child_nodes_info)
                local_nodes_info.append(node_info)

            return local_nodes_info

        nodes_info.extend(traverse_and_create_node_info(traverse_tree))

        material_data = MaterialData(
            material_name=selected_node.name(),
            textures={},  # Add textures information if needed
            nodes=nodes_info
        )

        print("Final MaterialData:")
        for node_info in material_data.nodes:
            print(f"Node: {node_info.node_name}, Type: {node_info.node_type}, Params: {node_info.parameters}, Path: {node_info.traversal_path}")
            for child_node in node_info.child_nodes:
                print(f"  Child Node: {child_node.node_name}, Type: {child_node.node_type}, Params: {child_node.parameters}, Path: {child_node.traversal_path}")

        return material_data


class NodeRecreator:
    def __init__(self, material_data: MaterialData, target_context: hou.Node, target_renderer='arnold'):
        self.material_data = material_data
        self.target_context = target_context
        self.target_renderer = target_renderer
        self.old_new_node_map = {}

    def recreate_nodes(self):
        self._create_all_nodes(self.material_data.nodes)
        self._set_node_inputs(self.material_data.nodes)

    def _create_all_nodes(self, nodes: List[NodeInfo]):
        for node_info in nodes:
            print(f"\nCreating node: {node_info.node_name} of type {node_info.node_type}")
            new_node = self._create_node(node_info)
            self.old_new_node_map[node_info.traversal_path] = new_node
            # print(f"{self.old_new_node_map=}\n")
            self._create_all_nodes(nodes=node_info.child_nodes)

    def _create_node(self, node_info: NodeInfo) -> hou.Node:
        new_node_type = self._convert_node_type(node_info.node_type)
        new_node = self.target_context.createNode(new_node_type, node_info.node_name)
        print(f"{node_info.parameters=}")
        self.apply_parameters(new_node, node_info.parameters)
        return new_node

    def _set_node_inputs(self, nodes: List[NodeInfo]):
        for node_info in nodes:
            new_node = self.old_new_node_map[node_info.traversal_path]
            self._set_inputs_recursive(node_info, new_node)

    def _set_inputs_recursive(self, node_info: NodeInfo, new_node: hou.Node):
        for child_info in node_info.child_nodes:
            child_node = self.old_new_node_map[child_info.traversal_path]
            if child_info.connected_input_index is not None:
                new_node.setInput(child_info.connected_input_index, child_node)
            self._set_inputs_recursive(child_info, child_node)

    def _convert_node_type(self, node_type: str) -> str:
        """
        Convert the node type based on the target renderer.
        """
        conversion_map = {
            'arnold': {
                'mtlxstandard_surface': 'arnold::standard_surface',
                'mtlximage': 'arnold::image'
                # Add more conversions as needed
            },
            'mtlx': {
                'arnold::standard_surface': 'mtlxstandard_surface',
                'arnold::image': 'mtlximage'
                # Add more conversions as needed
            }
            # Add more renderer maps as needed
        }

        if self.target_renderer in conversion_map and node_type in conversion_map[self.target_renderer]:
            return conversion_map[self.target_renderer][node_type]
        return node_type  # Default to the original type if no conversion is found

    @staticmethod
    def apply_parameters(node: hou.Node, parameters: List[NodeParameter]):
        for param in parameters:
            # Determine the renderer-specific name using the standardized name
            node_type = node.type().name()
            node_specific_dict = TraverseNodeConnections.STANDARDIZED_PARAM_NAMES.get(node_type, {})
            if not node_specific_dict:
                raise Exception(f"Couldn't get dictionary for node type: {node_type}")

            # Reverse lookup: find the key (renderer-specific name) that matches the standardized name
            renderer_specific_name = next(
                (key for key, value in node_specific_dict.items() if value == param.standardized_name), None)

            hou_parm = node.parm(renderer_specific_name)
            if hou_parm is not None:
                hou_parm.set(param.value)
            else:
                print(f"Parameter '{renderer_specific_name}' not found on node '{node.path()}', \n{node_specific_dict=}")


def run(selected_node, target_context, target_renderer='mtlx'):
    """
    Temp run function that traverses mtlx networks then recreates it,
    with an option to specify the target renderer for material conversion.

    Args:
        selected_node (hou.Node): The selected Houdini node.
        target_context (hou.Node): The target context node where the recreated material nodes will be placed.
        target_renderer (str): The target renderer for material conversion ('arnold', 'mtlx', 'principled_shader', 'usdpreview').
    """
    # Create an instance of TraverseNodeConnections
    traverse_class = TraverseNodeConnections()

    # Traverse the children nodes of the selected node
    traverse_tree = traverse_class.traverse_children_nodes(selected_node)

    # Create material data with filtered parameters
    material_data = traverse_class.create_material_data(selected_node)

    # Recreate nodes for the specified renderer
    recreator = NodeRecreator(material_data, target_context, target_renderer)
    recreator.recreate_nodes()

    print(f"Material conversion complete. New material created in {target_renderer} format.")









