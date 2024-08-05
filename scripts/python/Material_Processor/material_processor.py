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
    from scripts.python.Material_Processor.material_classes import MaterialData, NodeInfo, NodeParameter
except:
    import Material_Processor.material_classes
    reload(Material_Processor.material_classes)
    from Material_Processor.material_classes import MaterialData, NodeInfo, NodeParameter

try:
    import hou
except:
    # temp to make the module work with substance painter
    hou = None




###################################### CONSTANTS ######################################

GENERIC_NODE_TYPES = {
    'arnold::standard_surface': 'GENERIC::standard_surface',
    'arnold::image': 'GENERIC::image',
    'arnold::color_correct': 'GENERIC::color_correct',
    # 'arnold_material': 'GENERIC::output',

    'mtlxstandard_surface': 'GENERIC::standard_surface',
    'mtlximage': 'GENERIC::image',
    'mtlxcolorcorrect': 'GENERIC::color_correct',
    'mtlxdisplacement': 'GENERIC::displacement',
    # 'subnetconnector': 'GENERIC::output',
    'null': 'GENERIC::null'
}



"""
Conversion_map is a dict of 'from_node_type' : 'to_node_type'
"""
CONVERSION_MAP = {
            'arnold': {
                'GENERIC::standard_surface': 'arnold::standard_surface',
                'GENERIC::image': 'arnold::image',
                'GENERIC::color_correct': 'arnold::color_correct',
                # 'GENERIC::output': 'arnold_material',
                'GENERIC::null': 'null'
            },
            'mtlx': {
                'GENERIC::standard_surface': 'mtlxstandard_surface',
                'GENERIC::image': 'mtlximage',
                'GENERIC::color_correct': 'mtlxcolorcorrect',
                'GENERIC::displacement': 'mtlxdisplacement',
                # 'GENERIC::output': 'subnetconnector',
                'GENERIC::null': 'null'
            }
        }

OUTPUT_NODE_MAP = {
    'arnold': 'arnold_material',
    'mtlx': 'subnetconnector'
}


"""
names of parameters on specific node which is supported in this module. Any other node type will be filtered out.
"""
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
    'mtlxcolorcorrect': {
        'saturation': 'saturation',
        'gamma': 'gamma',
        'gain': 'gain',
        'contrast': 'contrast',
        'exposure': 'exposure',
    },
    'mtlxdisplacement': {
        'displacement': 'displacement',
        'scale': 'scale',
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
    'arnold::color_correct': {
        'gamma': 'gamma',
        'saturation': 'saturation',
        'contrast': 'contrast',
        'exposure': 'exposure',
    },

    'principledshader::2.0': {
        'basecolor': 'base_color',
        'metallic': 'metalness',
        'rough': 'specular_roughness',
        'ior': 'specular_IOR',
        'reflect': 'specular',
        'difftrans': 'transmission',
        'emission': 'emission',
        'opaccolor': 'opacity',
        'subsurface': 'subsurface',
        'subtint': 'subsurface_color',
        'basecolorr': 'base_colorr',
        'basecolorg': 'base_colorg',
        'basecolorb': 'base_colorb',
        'sheen': 'sheen',
        'sheencolor': 'sheen_color',
        'coat': 'coat',
        'coatrough': 'coat_roughness',
        'coatior': 'coat_IOR',
        'coatcolorr': 'coat_colorr',
        'coatcolorg': 'coat_colorg',
        'coatcolorb': 'coat_colorb'
    }
}

OUTPUT_CONNECTIONS_INDEX_MAP = {
            'arnold': {
                'GENERIC::output_surface': 0,
                'GENERIC::output_displacement': 1
            },
            'mtlx': {
                'GENERIC::output_surface': 0,
                'GENERIC::output_displacement': 0
            }
        }


##########################################################################################




class NodeTraverser:
    """
    Class for traversing Houdini nodes to extract their connections and output nodes.
    """

    def __init__(self, material_type: str) -> None:
        """
        Initialize the NodeTraverser with the specified material type.

        Args:
            material_type (str): The type of material (e.g., 'arnold', 'mtlx', 'principledshader').
        """
        self.material_type = material_type
        self.output_nodes = {}

    def traverse_node_tree(self, node: hou.Node, path=None) -> Dict[hou.Node, Dict]:
        """
        Recursively traverse the node tree and return a dictionary of node connections.

        Args:
            node (hou.Node): The current Houdini node.
            path (list[hou.Node], optional): The traversal path.

        Returns:
            Dict[hou.Node, Dict]: A dictionary representing the node tree.
        """
        if path is None:
            path = []
        node_dict = {node: {}}

        if not node.inputs():
            return node_dict

        for input_node in node.inputs():
            if not input_node:
                continue

            input_index = None
            for input in node.inputConnections():
                if input.inputNode() == input_node:
                    input_index = input.inputIndex()
                    break

            input_node_dict = self.traverse_node_tree(input_node, path + [node])
            node_dict[node][(input_node, input_index)] = input_node_dict[input_node]

        return node_dict

    def traverse_children_nodes(self, parent_node: hou.Node) -> Dict:
        """
        Traverse the children nodes of a parent node to extract the node tree and detect output nodes.

        Args:
            parent_node (hou.Node): The parent Houdini node.

        Returns:
            Dict: A dictionary representing the node tree of the children nodes.
        """
        output_nodes = []
        for child in parent_node.children():
            is_output = True
            for other_node in parent_node.children():
                if child in other_node.inputs():
                    is_output = False
                    break
            if is_output:
                output_nodes.append(child)

        all_branches = {}
        for output_node in output_nodes:
            branch_dict = self.traverse_node_tree(output_node, [])
            all_branches.update(branch_dict)

        self.output_nodes = self.detect_output_nodes(parent_node, material_type=self.material_type)
        print(f"output nodes detected: {self.output_nodes}\n")

        print('traverse_children_nodes()-----all_branches:')
        pprint(all_branches, indent=3)
        print(f'\n')
        self.nested_nodes_dict = all_branches
        return all_branches


    @staticmethod
    def detect_output_nodes(parent_node: hou.Node, material_type: str) -> Dict:
        """
        Detect output nodes in the node tree based on the material type.

        Args:
            parent_node (hou.Node): The parent Houdini node.
            material_type (str): The type of material (e.g., 'arnold', 'mtlx', 'principledshader').

        Returns:
            Dict: A dictionary of detected output nodes.
        """
        print(f"detect_output_nodes START for {parent_node.path()}")
        if material_type == 'arnold':
            output_nodes = NodeTraverser._detect_arnold_output_nodes(parent_node)
        elif material_type == 'mtlx':
            output_nodes = NodeTraverser._detect_mtlx_output_nodes(parent_node)
        elif material_type == 'principledshader':
            output_nodes = NodeTraverser._detect_principled_output_nodes(parent_node)
        else:
            raise KeyError(f"Unsupported renderer: {material_type=}")

        return output_nodes

    @staticmethod
    def _detect_arnold_output_nodes(parent_node: hou.Node) -> Dict:
        """
        Detect Arnold output nodes in the node tree.

        Args:
            parent_node (hou.Node): The parent Houdini node.

        Returns:
            Dict: A dictionary of detected Arnold output nodes.
        """
        arnold_output = None
        for child in parent_node.children():
            if child.type().name() == 'arnold_material':
                arnold_output = child
                break
        if not arnold_output:
            raise Exception(f"No Output Node detected for Arnold Material")

        output_nodes = {}
        connections = arnold_output.inputConnections()
        for connection in connections:
            connected_input = connection.inputNode()
            connected_input_index = connection.outputIndex()
            connected_output_index = connection.inputIndex()
            if connected_output_index == 0:
                output_nodes['surface'] = {
                    'node': arnold_output,
                    'node_path': arnold_output.path(),
                    'connected_node': connected_input,
                    'connected_node_index': connected_input_index,
                    'generic_type': 'GENERIC::output_surface'
                }
            elif connected_output_index == 1:
                output_nodes['displacement'] = {
                    'node': arnold_output,
                    'node_path': arnold_output.path(),
                    'connected_node': connected_input,
                    'connected_node_index': connected_input_index,
                    'generic_type': 'GENERIC::output_displacement'
                }
        return output_nodes

    @staticmethod
    def _detect_mtlx_output_nodes(parent_node: hou.Node) -> Dict:
        """
        Detect MaterialX output nodes in the node tree.

        Args:
            parent_node (hou.Node): The parent Houdini node.

        Returns:
            Dict: A dictionary of detected MaterialX output nodes.
        """
        output_nodes = {}
        output_nodes_list = [child for child in parent_node.children() if child.type().name() == 'subnetconnector']

        for output_node in output_nodes_list:
            connections = output_node.inputConnections()
            for connection in connections:
                connected_input = connection.inputNode()
                connected_input_index = connection.outputIndex()
                connected_output_index = connection.inputIndex()
            parmname = output_node.parm('parmname').eval()
            if parmname in ['surface', 'displacement']:
                output_nodes[parmname] = {
                    'node': output_node,
                    'node_path': output_node.path(),
                    'connected_node': connected_input,
                    'connected_node_index': connected_input_index
                }
        return output_nodes

    @staticmethod
    def _detect_principled_output_nodes(parent_node: hou.Node) -> Dict:
        """
        Detect Principled Shader output nodes in the node tree.

        Args:
            parent_node (hou.Node): The parent Houdini node.

        Returns:
            Dict: A dictionary of detected Principled Shader output nodes.
        """
        output_nodes = {}
        for child in parent_node.children():
            if child.type().name() == 'principledshader::2.0':
                output_nodes['surface'] = {
                    'node': child,
                    'node_path': child.path(),
                    'generic_type': 'GENERIC::output_surface'
                }
            elif child.type().name() == 'displacement':
                output_nodes['displacement'] = {
                    'node': child,
                    'node_path': child.path(),
                    'generic_type': 'GENERIC::output_displacement'
                }
        return output_nodes

    def traverse_principled_shader(self, node: hou.Node) -> Dict:
        """
        Traverse the Principled Shader node to extract its parameters.

        Args:
            node (hou.Node): The Principled Shader Houdini node.

        Returns:
            Dict: A dictionary representing the node tree of the Principled Shader node.
        """
        parameters = self.extract_principled_parameters(node)
        print(f"{parameters=}")

        node_dict = {
            node: {
                'parameters': parameters,
                'children': {}
            }
        }
        return node_dict

    @staticmethod
    def extract_principled_parameters(node: hou.Node) -> List[NodeParameter]:
        """
        Extract parameters from a Principled Shader node.

        Args:
            node (hou.Node): The Principled Shader Houdini node.

        Returns:
            List[NodeParameter]: A list of extracted node parameters.
        """
        node_type = node.type().name()
        filtered_param_names = []
        standardized_names = STANDARDIZED_PARAM_NAMES.get(node_type, {})
        try:
            filtered_param_names = list(STANDARDIZED_PARAM_NAMES.get(node_type).keys())
        except AttributeError:
            print(f"WARNING: node_type: {node_type} not in STANDARDIZED_PARAM_NAMES dict")

        node_parameters = [NodeParameter(name=p.name(), value=p.eval(),
                                         standardized_name=standardized_names.get(p.name(), p.name()))
                           for p in node.parms() if p.name() in filtered_param_names
                           ]
        return node_parameters



class NodeStandardizer:
    """
    Class for standardizing Shader nodes and creating MaterialData Class.
    """

    def __init__(self, node_traverser: NodeTraverser, material_type, input_material_builder_node):
        self.node_traverser = node_traverser
        self.traverse_tree = node_traverser.nested_nodes_dict
        self.material_type = material_type
        self.output_nodes = node_traverser.output_nodes  # Add this line
        self.input_material_builder_node = input_material_builder_node  # Add this line

        self.standardize_output_nodes()
        self.create_standardized_material_data()

    def convert_parms_to_dict(parms_list: List[hou.Parm]) -> List[Dict[str, str]]:
        """
        Convert a list of hou.Parm objects to a list of dictionaries with name and value.

        Args:
            parms_list (List[hou.Parm]): The list of hou.Parm objects.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries with parameter names and values.
        """
        return [{'name': p.name(), 'value': p.eval()} for p in parms_list]

    def standardize_output_nodes(self) -> Dict:

        output_nodes: Dict = self.node_traverser.output_nodes
        standardized_output_nodes = {}
        for key, value in output_nodes.items():
            standardized_key = f"GENERIC::output_{key}"
            relative_path = value['node'].path().replace(f"{self.input_material_builder_node.path()}/", "")
            standardized_output_nodes[standardized_key] = {
                'node_path': relative_path,
                'connected_node': value['connected_node'],
                'connected_node_index': value['connected_node_index']
            }
        self.standardized_output_nodes = standardized_output_nodes
        return standardized_output_nodes

    @staticmethod
    def standardize_shader_node(node: hou.Node, connected_input_index: int, is_output_node=False,
                                output_type=None) -> NodeInfo:
        """
        Create a NodeInfo object from a node.

        Args:
            node (hou.Node): The Houdini node.
            connected_input_index (int): The index of the connected input.
            is_output_node (bool, optional): Whether the node is an output node.
            output_type (str, optional): The generic type of the output node.

        Returns:
            NodeInfo: The created NodeInfo object.
        """
        node_path = node.path()
        node_type = node.type().name()
        parms_list = NodeStandardizer.convert_parms_to_dict(node.parms())
        parameters = NodeStandardizer.standardize_shader_parameters(node_type, parms_list)
        generic_node_type = GENERIC_NODE_TYPES.get(node_type)

        return NodeInfo(
            node_type=generic_node_type,
            node_name=node.name(),
            parameters=parameters,
            node_path=node_path,
            connected_input_index=connected_input_index,
            child_nodes=[],
            is_output_node=is_output_node,
            output_type=output_type if is_output_node else generic_node_type
        )

    @staticmethod
    def standardize_shader_parameters(node_type, parms) -> List[NodeParameter]:
        """
        Filter and standardize parameters for a given node.

        Args:
            node_type (str): The type of the Houdini node.
            parms (List[Dict[str, str]]): The list of parameter dictionaries to be standardized.

        Returns:
            List[NodeParameter]: A list of filtered and standardized node parameters.
        """
        standardized_names = STANDARDIZED_PARAM_NAMES.get(node_type, {})

        filtered_param_names = []
        if STANDARDIZED_PARAM_NAMES.get(node_type):
            filtered_param_names = list(STANDARDIZED_PARAM_NAMES.get(node_type).keys())
        else:
            print(f"WARNING: node_type: {node_type} not in STANDARDIZED_PARAM_NAMES dict")

        node_parameters = [NodeParameter(name=param['name'], value=param['value'],
                                         standardized_name=standardized_names.get(param['name']))
                           for param in parms if param['name'] in filtered_param_names]
        return node_parameters

    def traverse_node_tree(self, node_dict: Dict) -> List[NodeInfo]:
        """
        Recursively traverse the node dictionary and create a list of NodeInfo objects.

        Args:
            node_dict (Dict): The node dictionary to traverse.

        Returns:
            List[NodeInfo]: A list of NodeInfo objects.
        """

        def extract_node_and_index(key) -> tuple:
            """
            Extract node and connected input index from the key.

            Args:
                key: The key from the node dictionary.

            Returns:
                tuple: The node and connected input index.
            """
            if isinstance(key, tuple):
                return key[0], key[1]
            else:
                return key, None

        local_nodes_info = []
        for key, children in node_dict.items():
            node, connected_input_index = extract_node_and_index(key)
            is_output_node = False
            output_type = None

            if node.type().name() in OUTPUT_NODE_MAP.values():
                is_output_node = True
                output_type = GENERIC_NODE_TYPES.get(node.type().name())

            node_info = self.standardize_shader_node(node, connected_input_index, is_output_node, output_type)
            child_nodes_info = self.traverse_node_tree(children)
            node_info.child_nodes.extend(child_nodes_info)
            local_nodes_info.append(node_info)

        return local_nodes_info

    @staticmethod
    def standardize_custom_tree(custom_node_tree: Dict, material_name: str) -> MaterialData:
        """
        Manually create a standardized traverse tree from custom tree dict with node names, paths, generic types, and parameters.

        Args:
            custom_node_tree (Dict): The custom tree provided by the user with node names, paths, generic types, and parameters.
            material_name (str): The name of the material.

        Returns:
            MaterialData: The created MaterialData object.
        """

        def traverse_tree(tree: Dict, parent_input_index=None) -> List[NodeInfo]:
            node_info_list = []
            for node_name, node_data in tree.items():
                generic_node_type = node_data['generic_type']
                is_output_node = 'output' in generic_node_type
                parameters = NodeStandardizer.standardize_shader_parameters(generic_node_type,
                                                                            node_data.get('parameters', []))
                connections = node_data.get('connections', {})

                node_info = NodeInfo(
                    node_type=generic_node_type,
                    node_name=node_name,
                    parameters=parameters,
                    node_path=node_name,
                    connected_input_index=parent_input_index,
                    child_nodes=[],
                    is_output_node=is_output_node,
                    output_type=generic_node_type if is_output_node else None
                )

                child_nodes_info = traverse_tree(connections)
                node_info.child_nodes.extend(child_nodes_info)
                node_info_list.append(node_info)

            return node_info_list

        nodes_info_list = traverse_tree(custom_node_tree)
        return MaterialData(material_name=material_name, nodes=nodes_info_list)

    def create_standardized_material_data(self) -> MaterialData:
        nodes_info_list = self.traverse_node_tree(self.traverse_tree)
        print(f"DEBUG: {nodes_info_list=}")

        output_connections = {}
        for output_type, output_info in self.output_nodes.items():
            connected_node = output_info.get('connected_node')
            if connected_node:
                connected_node_path = connected_node.path()
                connected_node_info = next(
                    (node_info for node_info in nodes_info_list if node_info.node_path == connected_node_path),
                    None
                )
                if connected_node_info:
                    output_connections[output_type] = connected_node_info

        material_data = MaterialData(
            material_name=self.input_material_builder_node.name(),
            nodes=nodes_info_list,
            output_connections=output_connections
        )

        self.material_data = material_data
        return material_data





class NodeRecreator:
    """
    Class for recreating Houdini nodes in a target renderer context.
    """

    def __init__(self, standardizer: NodeStandardizer, target_context, target_renderer='arnold'):
        """
        Initialize the NodeRecreator with the provided material data and target context.

        Args:
            standardizer
            target_context (hou.Node): The target Houdini context node.
            target_renderer (str, optional): The target renderer (default is 'arnold').
            traverse_class (class, optional): The class used for node traversal.
        """
        self.standardizer = standardizer
        self.target_context = target_context
        self.target_renderer = target_renderer
        self.old_new_node_map = {}  # a dict of {old_node.path():str : new_node:hou.Node}
        self.reused_nodes = {}

    @staticmethod
    def create_init_mtlx_shader(matnet=None):
        """
        Create an initial MaterialX shader in the specified network.

        Args:
            matnet (hou.Node, optional): The Houdini network node.

        Returns:
            Tuple[hou.Node, Dict]: The created MaterialX shader node and output nodes.
        """
        import voptoolutils
        UTILITY_NODES = 'parameter constant collect null genericshader'
        SUBNET_NODES = 'subnet subnetconnector suboutput subinput'
        MTLX_TAB_MASK = 'MaterialX {} {}'.format(UTILITY_NODES, SUBNET_NODES)
        name = 'mtlxmaterial'
        folder_label = 'MaterialX Builder'
        render_context = 'mtlx'

        if not matnet:
            matnet = hou.node('/mat')
        subnet_node = matnet.createNode('subnet', name)
        subnet_node = voptoolutils._setupMtlXBuilderSubnet(subnet_node=subnet_node, name=name, mask=MTLX_TAB_MASK,
                                                           folder_label=folder_label, render_context=render_context)
        output_nodes = {
            'GENERIC::output_surface': {'node': subnet_node.node('surface_output'),
                                        'node_path': subnet_node.node('surface_output').path()},
            'GENERIC::output_displacement': {'node': subnet_node.node('displacement_output'),
                                             'node_path': subnet_node.node('displacement_output').path()}
        }
        return subnet_node, output_nodes

    @staticmethod
    def create_init_arnold_shader(matnet=None):
        """
        Create an initial Arnold shader in the specified network.

        Args:
            matnet (hou.Node, optional): The Houdini network node.

        Returns:
            Tuple[hou.Node, Dict]: The created Arnold shader node and output nodes.
        """
        if not matnet:
            matnet = hou.node('/mat')
        node_material_builder = matnet.createNode('arnold_materialbuilder')
        output_nodes = {
            'GENERIC::output_surface': {'node': node_material_builder.node('OUT_material'),
                                        'node_path': node_material_builder.node('OUT_material').path()},
            'GENERIC::output_displacement': {'node': node_material_builder.node('OUT_material'),
                                             'node_path': node_material_builder.node('OUT_material').path()}
        }
        return node_material_builder, output_nodes

    def create_output_nodes(self):
        """
        Create or reuse output nodes in the target context.
        """
        output_node_type = OUTPUT_NODE_MAP.get(self.target_renderer)  # e.g. 'arnold_material' or 'subnetconnector'
        print(f"DEBUG: {self.created_output_nodes=}")
        print(f"DEBUG: {self.standardizer.output_nodes=}")
        for output_type, output_info in self.standardizer.output_nodes.items():
            # Check if the output node already exists in the target context
            # TODO: self.standardizer.output_nodes should be GENERIC types instead of 'surface' and 'displacement'
            created_output_node: hou.Node = self.created_output_nodes[output_type]['node']
            if created_output_node:
                node = created_output_node
                print(
                    f"Reusing existing output node: {node.path()} of type {output_node_type} for output {output_type}")
            else:
                node = self.material_builder.createNode(output_node_type, output_info['node'].name())
                print(f"Created new output node: {node.path()} of type {output_node_type} for output {output_type}")

            self.old_new_node_map[output_info['node_path']] = node
            self.created_output_nodes[output_type]['node'] = node
            print(f"DEBUG: create_oputput_nodes, {self.created_output_nodes=}")

    def _create_nodes_recursive(self, nodes: List[NodeInfo], processed_nodes=None):
        """
        Recursively create nodes from NodeInfo objects.

        Args:
            nodes (List[NodeInfo]): The list of NodeInfo objects.
            processed_nodes (set, optional): A set of processed node paths.
        """
        if processed_nodes is None:
            processed_nodes = set()

        for node_info in nodes:
            if node_info.node_path in processed_nodes:
                print(f"DEBUG: Skipping already created node {node_info.node_name} of type {node_info.node_type}")
                continue

            print(f"Creating node: {node_info.node_name} of type {node_info.node_type}")
            new_node = self._create_node(node_info)
            if not new_node:
                print(f"DEBUG: Couldn't create new node {node_info.node_type}")
                continue

            self.old_new_node_map[node_info.node_path] = new_node
            processed_nodes.add(node_info.node_path)
            self._create_nodes_recursive(nodes=node_info.child_nodes, processed_nodes=processed_nodes)

            # Add output nodes to the map if they are marked as such
            if node_info.is_output_node:
                print(f"DEBUG: Output node detected: {node_info.node_name} of type {node_info.node_type}")
                self.old_new_node_map[node_info.node_path] = new_node

    def _create_node(self, node_info: NodeInfo) -> hou.Node:
        """
        Create a Houdini node from NodeInfo.

        Args:
            node_info (NodeInfo): The NodeInfo object containing node information.

        Returns:
            hou.Node: The created Houdini node.
        """
        new_node_type = self._convert_generic_node_type_to_renderer_node_type(node_info.node_type,
                                                                              target_renderer=self.target_renderer)

        # Check for existing nodes of the same type to reuse
        existing_nodes = [node for node in self.material_builder.children() if
                          node.type().name() == new_node_type and node not in self.reused_nodes.values()]
        if existing_nodes:
            node = existing_nodes[0]
            print(f"Using existing node: {node.path()} of type {node.type().name()}")
            self.apply_parameters(node, node_info.parameters)
            self.reused_nodes[node_info.node_path] = node
            self.old_new_node_map[node_info.node_path] = node  # Ensure all nodes are mapped
            return node

        # Create new node if no reusable node is found
        new_node = self.material_builder.createNode(new_node_type, node_info.node_name)
        self.apply_parameters(new_node, node_info.parameters)
        self.reused_nodes[node_info.node_path] = new_node
        self.old_new_node_map[node_info.node_path] = new_node  # Ensure all nodes are mapped
        print(f"\n{self.old_new_node_map=}")
        return new_node

    def _set_node_inputs(self, nodes: List[NodeInfo]):
        """
        Set the inputs for the created nodes.

        Args:
            nodes (List[NodeInfo]): The list of NodeInfo objects.
        """
        for node_info in nodes:
            print(f"DEBUG: connecting node {node_info.node_path} of type {node_info.node_type}")

            # Skip setting inputs for output nodes
            if node_info.is_output_node:
                print(f"DEBUG: {node_info.node_type=} found in output nodes, skipping direct connection.")
                self._set_inputs_recursive(node_info, self.old_new_node_map.get(node_info.node_path))
                continue

            new_node = self.old_new_node_map.get(node_info.node_path)
            if not new_node:
                print(f"DEBUG: new_node is None for {node_info.node_path}.")
                continue

            self._set_inputs_recursive(node_info, new_node)

    def _set_inputs_recursive(self, node_info: NodeInfo, new_node: hou.Node):
        if new_node is None:
            print(f"DEBUG: new_node is None for {node_info.node_path}, skipping.")
            return

        for child_info in node_info.child_nodes:
            print(f"DEBUG: {child_info.node_type=}, {child_info.node_path=}")
            if child_info.is_output_node:
                print(f"DEBUG: {child_info.node_type=} found in output nodes, skipping direct connection.")
                continue  # Skip setting inputs for output nodes

            child_node = self.old_new_node_map.get(child_info.node_path)
            if not child_node:
                print(f"DEBUG: child_node is None for {child_info.node_path}.")
                continue

            if child_info.connected_input_index is not None:
                print(f"DEBUG: Setting input {child_info.connected_input_index} of {new_node=} to {child_node.path()}.")
                new_node.setInput(child_info.connected_input_index, child_node)
            else:
                print(f"DEBUG: connected_input_index is None for child node {child_info.node_path}.")

            self._set_inputs_recursive(child_info, child_node)

    def _convert_generic_node_type_to_renderer_node_type(self, node_type: str, target_renderer: str) -> str:
        """
        Convert a generic node type to a renderer-specific node type.

        Args:
            node_type (str): The generic node type.
            target_renderer (str): renderer type: e.g. 'arnold', 'mtlx'

        Returns:
            str: The renderer-specific node type.
        """
        # print(f"DEBUG: Generic node {node_type}, converted to: {CONVERSION_MAP[self.target_renderer][node_type]}")
        if node_type in CONVERSION_MAP[target_renderer]:
            return CONVERSION_MAP[target_renderer][node_type]
        else:
            return CONVERSION_MAP[target_renderer]['GENERIC::null']

    def create_nodes_from_material_data(self, material_data: MaterialData):
        """
        Create nodes in Houdini from the MaterialData object.

        Args:
            material_data (MaterialData): The MaterialData object containing standardized traverse tree.
        """

        def recursive_create_nodes(tree: List[NodeInfo], parent_node: hou.Node = None):
            for node_info in tree:
                new_node = self.material_builder.createNode(
                    self._convert_generic_node_type_to_renderer_node_type(node_info.node_type, self.target_renderer),
                    node_info.node_name)
                self.apply_parameters(new_node, node_info.parameters)
                self.old_new_node_map[node_info.node_name] = new_node

                # Recursively create child nodes
                recursive_create_nodes(node_info.child_nodes, new_node)

                # Set inputs for the new node
                for child_node_info in node_info.child_nodes:
                    input_index = child_node_info.connected_input_index
                    child_node = self.old_new_node_map.get(child_node_info.node_name)
                    if child_node and input_index is not None:
                        new_node.setInput(input_index, child_node)

        recursive_create_nodes(material_data.nodes)

    @staticmethod
    def apply_parameters(node: hou.Node, parameters: List[NodeParameter]):
        """
        Apply parameters to a Houdini node.

        Args:
            node (hou.Node): The Houdini node.
            parameters (List[NodeParameter]): The list of parameters to apply.
        """
        for param in parameters:
            node_type = node.type().name()
            node_specific_dict = STANDARDIZED_PARAM_NAMES.get(node_type)
            if not node_specific_dict:
                print(f"Couldn't get dictionary for node type: {node_type}")
                continue

            renderer_specific_name = next(
                (key for key, value in node_specific_dict.items() if value == param.standardized_name), None)

            hou_parm = node.parm(renderer_specific_name)
            if hou_parm is not None:
                hou_parm.set(param.value)
            else:
                print(f"Parm '{renderer_specific_name}' not found on node '{node.path()}',\n{node_specific_dict=}")

    def _set_output_connections(self):
        """
        Set connections for the output nodes in the recreated material.
        """
        renderer_output_connections = OUTPUT_CONNECTIONS_INDEX_MAP.get(self.target_renderer)
        if not renderer_output_connections:
            raise KeyError(f"Unsupported renderer: {self.target_renderer}")

        print(f"DEBUG: {self.created_output_nodes=}")
        for output_type, output_info in self.created_output_nodes.items():
            output_index = renderer_output_connections[output_type]
            output_node = output_info['node']

            if output_type not in renderer_output_connections:
                raise KeyError(f"{output_type=} not found in {renderer_output_connections=}")

            # Find the connected node info from the material_data output connections
            connected_node_info = self.standardizer.material_data.output_connections.get(output_type)
            if connected_node_info:
                new_node = self.old_new_node_map.get(connected_node_info.node_path)
                if new_node and new_node != output_node:
                    print(
                        f"DEBUG: {output_type=}, Setting input {output_index} of {output_node.path()} to {new_node.path()}")
                    output_node.setInput(output_index, new_node)
                else:
                    print(
                        f"DEBUG: New node for {output_type} not found in old_new_node_map or is the same as the output node.")
            else:
                # Ensure the existing output node is mapped correctly
                existing_output_node = self.old_new_node_map.get(output_info['node_path'])
                if existing_output_node:
                    self.old_new_node_map[output_info['node_path']] = existing_output_node
                    print(f"DEBUG: Reusing existing output node {existing_output_node.path()} for {output_type}")
                else:
                    print(f"DEBUG: No connected node info found for {output_type=}")

    def run(self):
        """
        Recreate the nodes in the target context based on the material data.
        """
        # Create the initial shader network based on the target renderer
        if self.target_renderer == 'mtlx':
            self.material_builder, self.created_output_nodes = self.create_init_mtlx_shader(self.target_context)
        elif self.target_renderer == 'arnold':
            self.material_builder, self.created_output_nodes = self.create_init_arnold_shader(self.target_context)
        else:
            raise Exception(f"Unsupported target renderer: {self.target_renderer}")

        # print(f"{self.material_builder=}, {self.standardizer.output_nodes=}, {self.created_output_nodes=}")

        # Create output nodes first
        print(f"\n\n\nDEBUG: STARTING create_output_nodes()....")
        self.create_output_nodes()

        # Proceed with node creation and input setting
        print(f"\n\n\nDEBUG: STARTING _create_all_nodes()....")
        self._create_nodes_recursive(self.standardizer.material_data.nodes)

        print(f"\n\n\nDEBUG: STARTING _set_node_inputs()....")
        self._set_node_inputs(self.standardizer.material_data.nodes)

        print(f"\n\n\nDEBUG: STARTING _set_output_connections()....")
        self._set_output_connections()



##############################################



def get_material_type(materialbuilder_node: hou.VopNode) -> str:
    """
    :param materialbuilder_node: input material shading network, e.g. arnold materialbuilder
    :return: str material type.
    """
    material_type = None

    if materialbuilder_node.type().name() == 'arnold_materialbuilder':
        material_type = 'arnold'
    elif materialbuilder_node.type().name() == 'subnet':
        for child_node in materialbuilder_node.children():
            if 'mtlx' in child_node.type().name():
                material_type = 'mtlx'
                break
    elif materialbuilder_node.type().name() == 'principledshader::2.0':
        material_type = 'principledshader'

    return material_type


def run(input_material_builder_node, target_context, target_renderer='arnold'):
    """
      Run the material conversion process for the selected node.

      Args:
          input_material_builder_node (hou.Node): The selected Houdini shading network,
                e.g. arnold materialbuilder or mtlx materialbuilder.
          target_context (hou.Node): The target Houdini context node.
          target_renderer (str, optional): The target renderer (default is 'mtlx').
    """
    material_type = get_material_type(input_material_builder_node)
    if not material_type:
        raise Exception(
            f"Couldn't determine Input material type, currently only Arnold, MTLX, and Principled Shader supported!")

    traverser = NodeTraverser(material_type=material_type)
    traverser.traverse_children_nodes(input_material_builder_node)

    # Pass output_nodes to NodeStandardizer
    standardizer = NodeStandardizer(node_traverser=traverser, material_type=material_type, input_material_builder_node=input_material_builder_node)

    print("\nFinal MaterialData:")
    for node_info in standardizer.material_data.nodes:  # 2 items in loop, surface and displacement if mtlx.
        print(f"{node_info=}\nchildren:-->")
        for child_node in node_info.child_nodes:
            print(f"'-->  Child Node Type: {child_node.node_type},"
                  f"Path: {child_node.node_path},"
                  f"children: {child_node.child_nodes}\n")

    recreator = NodeRecreator(standardizer, target_context, target_renderer)
    recreator.run()

    print(f"Material conversion complete. Converted material from {material_type} to {target_renderer}.")




def test():
    custom_tree = {
        'node1': {
            'generic_type': 'GENERIC::standard_surface',
            'parameters': [
                {'name': 'base', 'value': 1.0},
                {'name': 'specular', 'value': 0.5}
            ],
            'connections': {
                ('node2', 0): {
                    'generic_type': 'GENERIC::image',
                    'parameters': [
                        {'name': 'file', 'value': 'path/to/image.png'}
                    ],
                    'connections': {
                        ('node3', 0): {
                            'generic_type': 'GENERIC::color_correct',
                            'parameters': [
                                {'name': 'gamma', 'value': 2.2}
                            ],
                            'connections': {}
                        }
                    }
                }
            }
        }
    }

    material_name = "CustomMaterial"
    target_context = hou.node('/mat')

    standardized_material_data = NodeStandardizer.standardize_custom_tree(custom_tree, material_name)
    standardized_output_nodes = NodeStandardizer.standardize_output_nodes(custom_tree.get('output_nodes', {}))
    print(f"DEBUG: {standardized_material_data=}")

    recreator = NodeRecreator(standardized_material_data, standardized_output_nodes, target_context, target_renderer='mtlx')
    recreator.run()
    pprint(standardized_material_data)

