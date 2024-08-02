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
TODO: standardize the names so it can take any render engine and I dont have to repeat myself multiple times
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
    }

##########################################################################################




class TraverseNodeConnections:
    def __init__(self) -> None:
        self.output_nodes = {}
        self.output_connections = {}  # Initialize output_connections

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

        self.detect_output_nodes(parent_node)

        print('traverse_children_nodes()-----all_branches:')
        pprint(all_branches, indent=3)
        print(f'\n')
        return all_branches

    def detect_output_nodes(self, parent_node: hou.Node):
        print(f"detect_output_nodes START for {parent_node.path()}")
        for child in parent_node.children():
            if child.type().name() == 'arnold_material':
                self.output_nodes['surface'] = child
            elif child.type().name() == 'subnetconnector':
                parmname = child.parm('parmname').eval()
                if parmname == 'surface':
                    self.output_nodes['surface'] = child
                elif parmname == 'displacement':
                    self.output_nodes['displacement'] = child
        for key, node in self.output_nodes.items():
            self.output_nodes[key] = {
                'node': node,
                'traversal_path': node.path()
            }
        print(f"{self.output_nodes=}")

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
    def update_connected_input_indices(node_dict: Dict, node_info_list: List[NodeInfo]) -> None:
        for node_info in node_info_list:
            node = hou.node(node_info.traversal_path.split(">")[-1])
            index = TraverseNodeConnections.find_input_index_in_dict(node_dict, node)
            node_info.connected_input_index = index

    def filter_node_parameters(self, node: hou.Node) -> List[NodeParameter]:
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

    def create_material_data(self, selected_node: hou.Node) -> MaterialData:
        traverse_tree = self.traverse_children_nodes(selected_node)
        nodes_info = []

        def traverse_and_create_node_info(node_dict: Dict, parent_node: hou.Node = None):
            local_nodes_info = []
            for key, children in node_dict.items():
                if isinstance(key, tuple):
                    node = key[0]
                    connected_input_index = key[1]
                else:
                    node = key
                    connected_input_index = None

                if node.type().name() in OUTPUT_NODE_MAP.values():
                    # Traverse children of output nodes without adding the output node itself
                    local_nodes_info.extend(traverse_and_create_node_info(children))
                    continue

                parameters = self.filter_node_parameters(node)
                traversal_path = node.path()
                generic_node_type = GENERIC_NODE_TYPES.get(node.type().name(), node.type().name())

                node_info = NodeInfo(
                    node_type=generic_node_type,
                    node_name=node.name(),
                    parameters=parameters,
                    traversal_path=traversal_path,
                    connected_input_index=connected_input_index,
                    child_nodes=[]
                )

                # Recursively traverse and add child nodes information
                child_nodes_info = traverse_and_create_node_info(children)
                node_info.child_nodes.extend(child_nodes_info)

                local_nodes_info.append(node_info)

            return local_nodes_info

        nodes_info.extend(traverse_and_create_node_info(traverse_tree))

        material_data = MaterialData(
            material_name=selected_node.name(),
            textures={},
            nodes=nodes_info
        )

        print("\nFinal MaterialData:")
        for node_info in material_data.nodes:
            print(f"NodeType: {node_info.node_type}, Path: {node_info.traversal_path}")
            for child_node in node_info.child_nodes:
                print(f"'-->  Child Node Type: {child_node.node_type},"
                      f"Path: {child_node.traversal_path},"
                      f"children: {child_node.child_nodes}\n")

        return material_data


class NodeRecreator:
    def __init__(self, material_data: MaterialData, target_context: hou.Node, target_renderer='arnold', traverse_class=None, output_nodes=None):
        self.material_data = material_data
        self.target_context = target_context
        self.target_renderer = target_renderer
        self.old_new_node_map = {}  # a dict of {old_node.path():str : new_node:hou.Node}
        self.reused_nodes = {}
        self.output_node = None  # Track the output node for special handling
        self.traverse_class = traverse_class  # Reintroduce traverse_class
        self.output_nodes = output_nodes  # Add output_nodes attribute

    @staticmethod
    def create_init_mtlx_shader(matnet=None):
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
            'surface': {'node': subnet_node.node('surface_output'),
                        'traversal_path': subnet_node.node('surface_output').path()},
            'displacement': {'node': subnet_node.node('displacement_output'),
                             'traversal_path': subnet_node.node('displacement_output').path()}
        }
        return subnet_node, output_nodes

    @staticmethod
    def create_init_arnold_shader(matnet=None):
        if not matnet:
            matnet = hou.node('/mat')
        node_material_builder = matnet.createNode('arnold_materialbuilder')
        output_nodes = {
            'surface': {'node': node_material_builder.node('OUT_material'),
                        'traversal_path': node_material_builder.node('OUT_material').path()}
        }
        return node_material_builder, output_nodes

    def create_output_nodes(self):
        for key, output_info in self.output_nodes.items():
            new_node_type = OUTPUT_NODE_MAP.get(self.target_renderer)
            print(f"{new_node_type=}, {self.output_nodes=}")
            if not new_node_type:
                raise KeyError(f"Couldn't get New Output node type from dictionary, might be unsupported renderer!")

            # Check if the output node already exists in the target context
            existing_node = self.target_context.node(output_info['node'].name())
            if existing_node:
                node = existing_node
                print(f"Reusing existing output node: {node.path()} of type {new_node_type}")
            else:
                node = self.target_context.createNode(new_node_type, output_info['node'].name())
                print(f"Created new output node: {node.path()} of type {new_node_type}")

            # self.apply_parameters(node, output_info['node'].parms())  # Uncomment if you want to apply parameters
            self.old_new_node_map[output_info['traversal_path']] = node
            self.output_nodes[key]['node'] = node  # Update to the newly created or reused node


    def recreate_nodes(self):
        # Create the initial shader network based on the target renderer
        if self.target_renderer == 'mtlx':
            self.target_context, self.output_nodes = self.create_init_mtlx_shader(self.target_context)
        elif self.target_renderer == 'arnold':
            self.target_context, self.output_nodes = self.create_init_arnold_shader(self.target_context)
        else:
            raise Exception(f"Unsupported target renderer: {self.target_renderer}")

        print(f"{self.target_context=}, {self.output_nodes=}")

        # Create output nodes first
        print(f"\n\n\nDEBUG: STARTING create_output_nodes()....")
        self.create_output_nodes()

        # Proceed with node creation and input setting
        print(f"\n\n\nDEBUG: STARTING _create_all_nodes()....")
        self._create_all_nodes(self.material_data.nodes)

        print(f"\n\n\nDEBUG: STARTING _set_node_inputs()....")
        self._set_node_inputs(self.material_data.nodes)

        print(f"\n\n\nDEBUG: STARTING _set_output_connections()....")
        self._set_output_connections()

    def _create_all_nodes(self, nodes: List[NodeInfo], processed_nodes=None):
        if processed_nodes is None:
            processed_nodes = set()

        for node_info in nodes:
            if node_info.traversal_path in processed_nodes:
                print(f"DEBUG: Skipping already created node {node_info.node_name} of type {node_info.node_type}")
                continue

            print(f"\nCreating node: {node_info.node_name} of type {node_info.node_type}")
            new_node = self._create_node(node_info)
            if not new_node:
                print(f"DEBUG: Couldn't create new node {node_info.node_type}")
                continue

            self.old_new_node_map[node_info.traversal_path] = new_node
            processed_nodes.add(node_info.traversal_path)
            self._create_all_nodes(nodes=node_info.child_nodes, processed_nodes=processed_nodes)

            # Add output nodes to the map if they are marked as such
            if node_info.is_output_node:
                print(f"DEBUG: Output node detected: {node_info.node_name} of type {node_info.node_type}")
                self.old_new_node_map[node_info.traversal_path] = new_node

    def _create_node(self, node_info: NodeInfo) -> hou.Node:
        new_node_type = self._convert_node_type(node_info.node_type)
        if not new_node_type:
            print(f"DEBUG: Node type:{node_info.node_type} is unsupported")
            return None

        # Check for existing nodes of the same type to reuse
        existing_nodes = [node for node in self.target_context.children() if
                          node.type().name() == new_node_type and node not in self.reused_nodes.values()]
        if existing_nodes:
            node = existing_nodes[0]
            print(f"Using existing node: {node.path()} of type {node.type().name()}")
            self.apply_parameters(node, node_info.parameters)
            self.reused_nodes[node_info.traversal_path] = node
            self.old_new_node_map[node_info.traversal_path] = node  # Ensure all nodes are mapped
            return node

        # Create new node if no reusable node is found
        new_node = self.target_context.createNode(new_node_type, node_info.node_name)
        self.apply_parameters(new_node, node_info.parameters)
        self.reused_nodes[node_info.traversal_path] = new_node
        self.old_new_node_map[node_info.traversal_path] = new_node  # Ensure all nodes are mapped
        print(f"\n{self.old_new_node_map=}")
        return new_node

    def _set_node_inputs(self, nodes: List[NodeInfo]):
        print(f"\n\nDEBUG: STARTING _set_node_inputs()....")
        for node_info in nodes:
            print(f"DEBUG: connecting node {node_info.traversal_path} of type {node_info.node_type}")

            # Skip setting inputs for output nodes
            if node_info.node_type in OUTPUT_NODE_MAP.values():
                print(f"DEBUG: {node_info.node_type=} found in {OUTPUT_NODE_MAP.values()=}, skipping output node.")
                # Continue to process child nodes even for output nodes
                self._set_inputs_recursive(node_info, self.old_new_node_map.get(node_info.traversal_path))
                continue

            new_node = self.old_new_node_map.get(node_info.traversal_path)
            if not new_node:
                print(f"DEBUG: new_node is None for {node_info.traversal_path}.")
                continue

            self._set_inputs_recursive(node_info, new_node)

    def _set_inputs_recursive(self, node_info: NodeInfo, new_node: hou.Node):
        if new_node is None:
            print(f"DEBUG: new_node is None for {node_info.traversal_path}, skipping.")
            return

        for child_info in node_info.child_nodes:
            print(f"DEBUG: {child_info.node_type=}, {child_info.traversal_path=}")
            if child_info.node_type in OUTPUT_NODE_MAP.values():
                print(f"DEBUG: {child_info.node_type=} found in output nodes, skipping direct connection.")
                self._set_inputs_recursive(child_info, self.old_new_node_map.get(child_info.traversal_path))
                continue  # Skip setting inputs for output nodes

            child_node = self.old_new_node_map.get(child_info.traversal_path)
            if not child_node:
                print(f"DEBUG: child_node is None for {child_info.traversal_path}.")
                continue

            if child_info.connected_input_index is not None:
                print(
                    f"DEBUG: Setting input {child_info.connected_input_index} of {new_node=} to {child_node.path()}.")
                new_node.setInput(child_info.connected_input_index, child_node)
            else:
                print(f"DEBUG: connected_input_index is None for child node {child_info.traversal_path}.")

            self._set_inputs_recursive(child_info, child_node)

    def _convert_node_type(self, node_type: str) -> str:
        print(f"DEBUG: renderer:{self.target_renderer}, node_type:{node_type}")
        if node_type in ('arnold_material', 'subnetconnector'):
            if self.target_renderer == 'arnold':
                return 'arnold_material'
            elif self.target_renderer == 'mtlx':
                return 'subnetconnector'

        if self.target_renderer in CONVERSION_MAP and node_type in CONVERSION_MAP[self.target_renderer]:
            return CONVERSION_MAP[self.target_renderer][node_type]
        else:
            return CONVERSION_MAP[self.target_renderer]['GENERIC::null']

    @staticmethod
    def apply_parameters(node: hou.Node, parameters: List[NodeParameter]):
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
        output_connections = {
            'arnold': {
                'surface': 0,
                'displacement': 1
            },
            'mtlx': {
                'surface': 0,
                'displacement': 0
            }
        }

        renderer_output_connections = output_connections.get(self.target_renderer)
        if not renderer_output_connections:
            raise KeyError(f"Unsupported renderer: {self.target_renderer}")

        for key, output_info in self.output_nodes.items():
            output_node = output_info['node']
            if key not in renderer_output_connections:
                raise KeyError(f"{key=} not found in {renderer_output_connections=}")

            output_index = renderer_output_connections[key]
            connected_node_info = None

            if self.target_renderer == 'arnold':
                # For Arnold, gather all nodes connected to the output
                connected_nodes = []
                for node_info in self.material_data.nodes:
                    if node_info.node_type == 'GENERIC::standard_surface':  # Ensure we're only looking for standard surfaces
                        connected_nodes.append(node_info)
                for connected_node_info in connected_nodes:
                    new_node = self.old_new_node_map.get(connected_node_info.traversal_path)
                    print(
                        f"DEBUG: Arnold renderer - Trying to connect {new_node.path() if new_node else 'None'} to {output_node.path()} at index {output_index}")
                    if new_node and new_node != output_node:
                        print(f"DEBUG: Setting input {output_index} of {output_node.path()} to {new_node.path()}")
                        output_node.setInput(output_index, new_node)
                    else:
                        print(
                            f"DEBUG: New node for {key} not found in old_new_node_map or is the same as the output node.")
            else:
                # For MTLX or other renderers, assume only one child node connected directly to output
                for node_info in self.material_data.nodes:
                    if node_info.child_nodes:
                        for child_node in node_info.child_nodes:
                            if child_node.node_type == 'GENERIC::standard_surface':  # Ensure we're only looking for standard surfaces
                                connected_node_info = child_node
                                break
                if connected_node_info:
                    new_node = self.old_new_node_map.get(connected_node_info.traversal_path)
                    print(f"DEBUG: {connected_node_info=}")
                    if new_node and new_node != output_node:
                        print(f"DEBUG: Setting input {output_index} of {output_node.path()} to {new_node.path()}")
                        output_node.setInput(output_index, new_node)
                    else:
                        print(
                            f"DEBUG: New node for {key} not found in old_new_node_map or is the same as the output node.")
                else:
                    print(f"DEBUG: No connected node info found for output node {output_node.path()}")


def run(selected_node, target_context, target_renderer='arnold'):
    traverse_class = TraverseNodeConnections()

    material_data = traverse_class.create_material_data(selected_node)

    recreator = NodeRecreator(material_data, target_context, target_renderer, traverse_class, traverse_class.output_nodes)
    recreator.recreate_nodes()

    print(f"Material conversion complete. New material created in {target_renderer} format.")




