"""
copyright Ahmed Hindy. please mention the original author if you used any part of this code
"""

import hou
from typing import Dict
from pprint import pprint


class MaterialProcessor:
    """
    note: rename it to 'Ingest'
    """
    def __init__(self):
        global mysel
        # mysel = hou.selectedNodes()
        # self.safetycheck()

    @staticmethod
    def get_current_hou_context():
        """
        returns the current open tab in Houdini.
        """
        current_tab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, 0)
        current_tab_parent = current_tab.pwd()
        print(f"get_current_hou_context()----- {current_tab_parent.type().name()=}")
        return current_tab_parent

    def safetycheck(self):
        """
        SAFETY TO CHECK THE CURRENT SELECTION, IF NOTHING OR IF NOT A PRINCIPLE SHADER THEN SHOW A MESSAGE.
        not used so probably will be deleted
        """
        acceptable_material_node = ["principledshader::2.0", "arnold_materialbuilder", "rs_materialbuilder", "subnet"]

        if mysel==():
            hou.ui.displayMessage("Please select a principleShader to convert")
        else :
            type = mysel[0].type()
            if type.name() in acceptable_material_node:
                pass

            else:
                hou.ui.displayMessage("Current selected node is a : " + type.description() + """
                
                You need to select a node of type PrincipledShader""")
                return

    @staticmethod
    def get_principled_texture_nodes():
        """
        Get all Principled texture nodes in the current scene.
        note: make it work only on matnets instead of looping over all nodes in scene.
        note: currently not used
        """
        texture_nodes = []
        for node in hou.node("/").allSubChildren(recurse_in_locked_nodes=False):
            if node.type().name() == "principledshader::2.0":
                texture_nodes.append(node)
        return texture_nodes

    @staticmethod
    def convert_parm_list_to_dict(input_parm_list):
        """
        input  -> list of hou.parm objects, e.g., [<hou.Parm basecolor_texture in /mat/principledshader2>]
        output <- dict containing {parm_name: parm_obj}
                  e.g. {'basecolor_texture': <hou.Parm basecolor_texture in /mat/principledshader2>}
        """
        parm_dict = {}
        for parm in input_parm_list:
            parm_name = parm.name()
            parm_dict[parm_name] = parm
        return parm_dict

    @staticmethod
    def get_texture_parms_from_principled_shader(input_node) -> list[hou.parm]:
        """
        input  -> hou.node() of type 'principledshader::2.0'
        process: returns dict of parameters on a node that have '<tex_name>_useTexture' enabled
                 basically get all enabled texture parameters.
        output <- list containing all enabled texture parameters on the principled shader.
                  # e.g. {'basecolor_texture': <hou.Parm basecolor_texture in /mat/principledshader2>}
        """
        input_tex_parm_dict = {}
        input_tex_parm_list = []
        for parm in input_node.parms():
            if '_useTexture' in parm.name():
                if parm.eval() == 1:
                    input_tex_str  = parm.name().split('_useTexture')[0] + '_texture'
                    input_tex_parm = input_node.parm(input_tex_str)
                    # print(f'{input_tex_parm=}')
                    # input_tex_parm_dict[input_tex_str] = input_tex_parm
                    input_tex_parm_list.append(input_tex_parm)

        # special case for getting displacement
        if input_node.parm('dispTex_enable'):
            input_tex_str = 'displacement' + '_texture'
            input_tex_parm = input_node.parm('dispTex_texture')
            # input_tex_parm_dict[input_tex_str] = input_tex_parm
            input_tex_parm_list.append(input_tex_parm)

        print(f'{input_tex_parm_list=}')
        return input_tex_parm_list

    @staticmethod
    def get_texture_parms_from_arnold_shader(input_node: hou.node) -> list[hou.parm]:
        """
        input  -> hou.node() of type 'arnold_materialbuilder'
        process: 1. Traverses the shader network to find all 'arnold::image' nodes connected
                 2. returns dict of parameters on nodes 'arnold::image' that are connected to the shader
        output <- list of parameters on nodes 'arnold::image' that are connected to the shader
                  e.g. {'basecolor_texture': <hou.Parm basecolor_texture in /mat/principledshader2>}
        """
        traverse_class   = Traverse_Node_Connections()
        node_tree_dict   = traverse_class.traverse_children_nodes(input_node)
        found_nodes      = traverse_class.find_nodes_of_type(node_dict=node_tree_dict, node_type='arnold::image')
        found_parms      = [node.parm('filename') for node in found_nodes]

        print(f' ---->>> {found_parms=}\n')
        return found_parms

    @staticmethod
    def get_texture_parms_from_all_shader_types(input_node: hou.node) -> list[hou.parm]:
        input_tex_parm_list = []
        node_type = input_node.type().name()
        if node_type == 'principled_shader::2.0':
            input_tex_parm_list.extend(MaterialProcessor.get_texture_parms_from_principled_shader(input_node))
        if node_type == 'arnold_materialbuilder':
            input_tex_parm_list.extend(MaterialProcessor.get_texture_parms_from_arnold_shader(input_node))
        if node_type == 'subnet':
            pass
        return input_tex_parm_list

    @staticmethod
    def get_texture_maps_from_parms(input_parms_dict: Dict[str, hou.parm]) -> Dict[str, str]:
        """
        input  -> dict of {'parm_name' : hou.parm}
        process: gets the string value of parameter including '<UDIM>' if found
        output <- dict of {'parm_name' : parm.unexpandedString())
        """
        textures_dict = {}
        for key, value in input_parms_dict.items():
            parm_value = value.unexpandedString()
            textures_dict[key] = parm_value

        print(f'get_texture_maps_from_parms()-----{textures_dict=}')
        return textures_dict
    

    @staticmethod
    def normalize_texture_map_keys(texture_dict: Dict[str, str]) -> Dict[str, str]:
        """
        input  -> takes a dict from 'get_texture_maps_from_parms()'
        process: Normalizes the dict keys related to the names of the texture parameters,
                 because every render engine has its set of names. example for principledshader::2.0:
                 e.g. dict['basecolor_texture'] = value -> dict['albedo'] = value
        output <- dict with same value but keys are named differently (normalized)
        note:   not all textures are added for now
        note:   CRITICAL: only works for principled shader, for Arnold/mtlx we need to get the connection hierarchy
        """
        normalized_dict = {}

        for key, value in texture_dict.items():
            if any(k in key for k in ['albedo', 'diffuse', 'basecolor']):
                normalized_dict['albedo'] = value
            elif any(k in key for k in ['rough', 'roughness']):
                normalized_dict['roughness'] = value
            elif any(k in key for k in ['metal', 'metallness']):
                normalized_dict['metallness'] = value
            elif any(k in key for k in ['normal', 'normalmap', 'baseNormal']):
                normalized_dict['normal'] = value
            elif any(k in key for k in ['dispTex']):
                normalized_dict['displacement'] = value
            else:
                print(f"normalize_texture_map_keys()----- a texture_map_key wasn't processed:{key=} is {value=}")
                normalized_dict[key] = value

        return normalized_dict


# class NotUsed:
    # @staticmethod
    # def convert_principled_textures_to_arnold():
    #     """
    #     Convert all Principled texture nodes in the current scene to Arnold Standard Surface.
    #     """
    #     texture_nodes = get_principled_texture_nodes()
    #     for texture_node in texture_nodes:
    #         convert_texture_node_to_arnold(texture_node)
    #
    # # convert_principled_textures_to_arnold()


class Traverse_Node_Connections:
    """
    nice class but has no place in this module. move somewhere else
    """
    def __init__(self) -> None:
        pass
    
    def traverse_node_tree(self, node, path=[]) -> Dict[hou.node, hou.node]:
        """
        Recursively traverses the inputs of a given node, building a nested dictionary of connections.
        Args:
        - node: The node to traverse from.
        - path: The accumulated path of node names from the output node to the current node.
        Returns:
        A nested dictionary representing the connections from the given node.
        """
        # Initialize the dictionary for the current node
        node_dict = {node: {}}

        # Base case: if the node has no inputs, return the node name
        if node.inputs() is None or len(node.inputs()) == 0:
            return node_dict

        # Iterate through each input of the node
        for input_node in node.inputs():
            if input_node is not None:
                # Find the input index for the connection
                input_index = None
                for idx, input in enumerate(node.inputConnections()):
                    if input.inputNode() == input_node:
                        input_index = input.inputIndex()
                        # print(f'{input_index=}')

                        break

                # Recursively traverse the input node, building the dictionary
                input_node_dict = self.traverse_node_tree(input_node, path + [node])

                # Use a tuple (input_node, input_index) as key to include input index information
                node_dict[node][(input_node, input_index)] = input_node_dict[input_node]

        return node_dict


    def traverse_children_nodes(self, parent_node):
        """
        Executes the traversal and builds a nested dictionary of node connections starting from output nodes.
        Args:
        - node: The node to start the traversal from.
        Returns:
        A nested dictionary representing all node connection branches from the output nodes.
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

        print(f'traverse_children_nodes()-----{all_branches=}\n')
        return all_branches




    @staticmethod
    def find_input_index_in_dict(node_dict: dict, target_node: hou.node) -> int:
        """
        Searches through a nested dictionary for a specific node and returns its output index to the next connected node
        by finding the tuple that contains the node as the first item.
        input  -> - node_dict  : The nested dictionary that includes tuples of (node, input_index).
                  - target_node: The target node for which the input index is sought.
        output <- - int input index if the target node is found, None otherwise.
        note: this method can be used to look 'arnold::image' is connected where on a standard surface
              to do: 1- there might be intermediate nodes, we need to extend the function to look for a distance node
                        e.g., 'standard_surface1' for example
        note: currently unused, if not useful then delete
        """
        for key, value in node_dict.items():
            # Check if the key is a tuple (node, input_index), then compare node
            if isinstance(key, tuple) and key[0] == target_node:
                return key[1]
            # If the key itself is the node, we're looking at a parent node with no interest in input_index
            elif key == target_node:
                return None
            # If the value is a dict, recursively search this next level of the tree
            if isinstance(value, dict):
                result = Traverse_Node_Connections.find_input_index_in_dict(value, target_node)
                if result is not None:
                    return result
        # Node not found in this branch of the dictionary
        return None

    @staticmethod
    def get_input_index_to_target_node_type(node_dict: dict, node_a: hou.node, node_b_type: str) -> int:
        """
        generated from gpt4,
        process: given a connection from node_a all the way to a node_b with intermediate nodes, this method attempts
                to get the input connection index to node_b. method is currently limited to node_b.type().name(),
                 but I plan to extend it in the future. node_b_type can be the standard surface node for
                 Arnold, MTLX, RS_material builder and other Uber shaders.
                 e.g., would be: node_a= hou.node(/mat/ar_shd_net/image_albedo), node_b_type='arnold::standard_surface'
        """

        # Flatten the dictionary to a simpler structure that directly maps children to their parent and index
        def flatten_dict(d, flat_dict=None, parent=None):
            if flat_dict is None:
                flat_dict = {}
            for key, value in d.items():
                if isinstance(key, tuple):  # Node is in a tuple with its input index
                    node, index = key
                    flat_dict[node] = (parent, index)  # Map child node to its parent and index
                    flatten_dict(value, flat_dict, parent=node)
                else:
                    flatten_dict(value, flat_dict, parent=key)
            return flat_dict

        flat_dict = flatten_dict(node_dict)
        current_node = node_a

        while current_node:
            parent_info = flat_dict.get(current_node)
            if parent_info is None:
                # print(f"No further parent found for {current_node}.")
                break  # Break the loop if no parent info is available

            parent, index = parent_info
            if parent is None or parent.type().name() != node_b_type:
                # print(f"Moving up from {current_node} to its parent.")
                current_node = parent  # Move to the next parent in the hierarchy
                continue  # Continue traversing up the tree

            print(f"Connection to {node_b_type} found at index {index}.")
            return index  # Desired node type found, return the connection index

        # print(f"No connection from {node_a} to a node of type {node_b_type} found.")
        return None  # No connection to the specified node type found

    @staticmethod
    def map_all_nodes_to_target_input_index(node_dict, node_b_type='arnold::standard_surface'):
        """
        generated from gpt4,
        Iterates over each node in the nested dictionary, attempting to find the connection index
        to a node named 'standard_surface1' using the find_connection_to_surface function.

        Args:
        - node_dict: The nested dictionary representing node connections.
        - surface_name: The name of the surface node to find connections to.

        Returns:
        A dictionary mapping each node to its input index for the connection to 'standard_surface1',
        or None if no such connection is found for a particular node.
        """
        connection_indices = {}

        def iterate_nodes(d):
            for key, value in d.items():
                if isinstance(key, tuple):  # Check if the key is a tuple (node, input_index)
                    node, _ = key
                    index = Traverse_Node_Connections.get_input_index_to_target_node_type(node_dict, node, node_b_type)
                    connection_indices[node] = index
                    iterate_nodes(value)  # Recursively search in sub-dictionaries
                elif isinstance(value, dict):  # If the value is a dict, continue searching
                    iterate_nodes(value)

        iterate_nodes(node_dict)
        return connection_indices


    @staticmethod
    def find_nodes_of_type(node_dict, node_type: str, found_nodes=None) -> list[hou.node]:
        """
        A Recursive function that loops over a nested dictionary of hou.node objects. it filters a specific node type.
        takes node_dict from traverse_children_nodes()
        Args:
        - node_dict:  nested dictionary containing hou.node objects
        - node_type: The type of node to search for (e.g., 'arnold::image').
        - found_nodes: Accumulator for found nodes of the specified type, used inside
        Returns:
        A list of hou.node objects of specified type.
        note: I need to use it to get the texture 'file' parmater on a list of arnold::image nodes.
        """
        if found_nodes is None:
            found_nodes = []

        for node, inputs in node_dict.items():
            if node and node.type().name() == node_type:
                found_nodes.append(node)
            if isinstance(inputs, dict):  # If inputs is a dictionary, it means the node has connected inputs
                Traverse_Node_Connections.find_nodes_of_type(inputs, node_type, found_nodes)

        return found_nodes

    @staticmethod
    def map_connection_input_index_to_texture_type(input_dict: dict, renderer='Arnold'):
        """
        takes in a filtered input dictof only 'image' nodes, maps the connection_index to corresponding map type,
        then return a new dict:  {texture_type e.g. 'roughness': image_node e.g. '<hou.VopNode of type arnold::image>'}.
        e.g., of in_dict: {<hou.VopNode of type arnold::image at /mat/arnold_materialbuilder1/image_albedo>: 1,
                              <hou.VopNode of type arnold::image at /mat/arnold_materialbuilder1/image_rough>: 6}
        e.g., of out_dict:{'albedo': <hou.VopNode of type arnold::image at /mat/arnold_materialbuilder1/image_albedo>,
                           'roughness': <hou.VopNode of type arnold::image at /mat/arnold_materialbuilder1/image_rough>}
        """
        # Mapping of connection_index to map name
        if renderer == 'Arnold':
            index_map = {
                1: 'albedo',
                6: 'roughness',
                10: 'transmission',
                38: 'opacity',
                39: 'normal'}
        node_map_dict = {index_map[value]: key for key, value in input_dict.items() if value in index_map}

        print(f'{node_map_dict=}')
        return node_map_dict




class Convert:
    """
    this class creates material shading networks.
    input  -> dict? with list of all textures and shader attributes . Usually comes from another function that ingests input textures
    output <- new material shading network
    currently it creates multiple image nodes disregarding the input material
    note: rename to 'Create'
    """
    @staticmethod
    def create_usdpreview_shader(mat_context, node_name='') -> hou.node:
        """
        input  -> mat context to create shader in
        output <- new usdpreview subnetwork
        """
        matsubnet  = mat_context.createNode("subnet", node_name + "_usdpreview")
        usdmat     = matsubnet.createNode("usdpreviewsurface", node_name + "_usdpreview")

        albedo     = matsubnet.createNode("usduvtexture::2.0", "albedo")
        roughness  = matsubnet.createNode("usduvtexture::2.0", "roughness")
        primvar_st = matsubnet.createNode("usdprimvarreader", "usd_primvar_ST")

        primvar_st.parm("signature").set("float2")
        primvar_st.parm("varname").set("st")

        #connect USD MAT with textures
        usdmat.setInput(0, albedo, 4)
        usdmat.setInput(5, roughness, 4)

        #connect USD textures with primvar
        albedo.setInput(1, primvar_st, 0)
        roughness.setInput(1, primvar_st, 0)

        matsubnet.layoutChildren()
        return matsubnet

    @staticmethod
    def connect_usdpreview_textures(usdpreview_subnet: hou.VopNode, textures_dict: Dict) -> None:
        """
        links the texture paths from 'textures_dictionary' to the freshly created usdpreview shader.
        """
        # print(f'{textures_dictionary=}')
        for key, value in textures_dict.items():
            # print(f'connect_usdpreview_textures()-----{key=} , {value=}')
            tex = usdpreview_subnet.node(key)
            if tex:
                tex.parm("file").set(value)
            else:
                print(f'node {key=} is missing...')
                pass

    @staticmethod
    def convert_to_usdpreview(input_mat_node, mat_context, textures_dict):
        """takes a material VOP node and converts it to usdpreview mat builder"""
        input_node_name   = input_mat_node.name()
        usdpreview_subnet = Convert.create_usdpreview_shader(mat_context, input_node_name)
        Convert.connect_usdpreview_textures(usdpreview_subnet, textures_dict)
        return usdpreview_subnet

    @staticmethod
    def create_mtlx_shader(mat_context, node_name=''):
        matsubnet  = mat_context.createNode("subnet", node_name + "_materialX")

        ## DEFINE OUTPUT SURFACE
        surfaceoutput = matsubnet.createNode("subnetconnector", "surface_output")
        surfaceoutput.parm("parmname").set("surface")
        surfaceoutput.parm("parmlabel").set("Surface")
        surfaceoutput.parm("parmtype").set("surface")
        surfaceoutput.parm("connectorkind").set("output")

        ## DEFINE OUTPUT DISPLACEMENT
        dispoutput = matsubnet.createNode("subnetconnector", "displacement_output")
        dispoutput.parm("parmname").set("displacement")
        dispoutput.parm("parmlabel").set("Displacement")
        dispoutput.parm("parmtype").set("displacement")
        dispoutput.parm("connectorkind").set("output")

        # CREATE MATERIALX STANDARD
        mtlx = matsubnet.createNode("mtlxstandard_surface", "surface_mtlx")
        surfaceoutput.setInput(0, mtlx)

        # CREATE ALBEDO
        albedo = matsubnet.createNode("mtlximage", "albedo")
        mtlx.setInput(1, albedo)

        # CREATE METALLIC
        metal = matsubnet.createNode("mtlximage", "metallness")
        metal.parm("signature").set("0")
        mtlx.setInput(3, metal)

        # CREATE ROUGHNESS
        roughness = matsubnet.createNode("mtlximage", "roughness")
        roughness.parm("signature").set("0")
        mtlx.setInput(6, roughness)

        # CREATE NORMAL
        normal = matsubnet.createNode("mtlximage", "normal")
        normal.parm("signature").set("vector3")
        plugnormal = matsubnet.createNode("mtlxnormalmap")
        mtlx.setInput(40, plugnormal)
        plugnormal.setInput(0, normal)

        # CREATE DISPLACEMENT
        displacement  = matsubnet.createNode("mtlximage", "displacement")
        plugdisplace  = matsubnet.createNode("mtlxdisplacement")
        remapdisplace = matsubnet.createNode("mtlxremap", "offset_displace")
        # set image displace
        displacement.parm("signature").set("0")
        # SETTING INPUTS
        dispoutput.setInput(0, plugdisplace)
        plugdisplace.setInput(0, remapdisplace)
        remapdisplace.setInput(0, displacement)

        matsubnet.layoutChildren()
        return matsubnet

    @staticmethod
    def connect_mtlx_textures(mtlx_subnet: hou.VopNode, textures_dictionary: Dict) -> None:
        """
        currently this simply links the texture paths from 'textures_dictionary' to the freshly created mtlx std surface.
        next step is to get all chnanged parameters from the principled shader and apply it here
        """
        # print(f'{textures_dictionary=}')
        for key, value in textures_dictionary.items():
            print(f'{key=} , {value=}')
            tex = mtlx_subnet.node(key)
            if tex:
                tex.parm("file").set(value)
            else:
                print(f'node {key=} is missing...')
                break

    @staticmethod
    def convert_to_mtlx(input_mat_node, mat_context, textures_dict):
        """takes a material VOP node and converts it to MTLX mat builder"""
        input_node_name = input_mat_node.name()
        mtlx_subnet     = Convert.create_mtlx_shader(mat_context, input_node_name)
        Convert.connect_mtlx_textures(mtlx_subnet, textures_dict)
        return mtlx_subnet

    @staticmethod
    def create_arnold_shader(mat_context: hou.node, node_name: str) -> hou.node:
        arnold_builder   = mat_context.createNode("arnold_materialbuilder", node_name + "_arnold")

        ## DEFINE STANDARD SURFACE
        output_node      = arnold_builder.node('OUT_material')
        node_std_surface = arnold_builder.createNode("arnold::standard_surface")
        output_node.setInput(0, node_std_surface)

        # CREATE ALBEDO
        image_albedo    = arnold_builder.createNode("arnold::image", "albedo")
        node_std_surface.setInput(1, image_albedo)

        # CREATE ROUGHNESS
        image_roughness = arnold_builder.createNode("arnold::image", "roughness")
        node_std_surface.setInput(6, image_roughness)

        # CREATE NORMAL
        image_normal    = arnold_builder.createNode("arnold::image", "normal")
        normal_map      = arnold_builder.createNode("arnold::normal_map")
        normal_map.setInput(0, image_normal)
        node_std_surface.setInput(39, normal_map)

        arnold_builder.layoutChildren()
        return arnold_builder




    @staticmethod
    def connect_arnold_textures(arnold_subnet: hou.VopNode, textures_dictionary: Dict) -> None:
        """
        currently this simply links the texture paths from 'textures_dictionary' to the freshly created mtlx std surface.
        next step is to get all changed parameters from the principled shader and apply it here
        """
        # print(f'{textures_dictionary=}')
        for key, value in textures_dictionary.items():
            print(f'connect_arnold_textures()-----{key=} , {value=}')
            if key == 'albedo':
                value.parm("filename").set(value)
            else:
                print(f'node {key=} is missing...')
                # break


    @staticmethod
    def convert_to_arnold(input_mat_node, mat_context, textures_dict):
        """takes a material VOP node and converts it to arnold mat builder"""
        input_node_name   = input_mat_node.name()
        arnold_subnet     = Convert.create_arnold_shader(mat_context, input_node_name)
        Convert.connect_arnold_textures(arnold_subnet, textures_dict)

        return arnold_subnet


def run(convert_to='arnold'):
    """
    function creates both Arnold and MTLX textures successfully.
    to do:  - create usdpreview                                                           // DONE
            - only add image nodes for exisiting textures
            - currently only ingests principledshader::2.0, add arnold/ mtlx to the list
            - create usd with 'python' lop node
            - create usd with usd-core lib so the usd creation can happen outside houdini.
    """
    selected_nodes        = hou.selectedNodes()
    mat_context           = hou.node('/mat')
    for input_node in selected_nodes:
        enabled_tex_parms = MaterialProcessor.get_texture_parms_from_all_shader_types(input_node=input_node)
        print(f'{input_node=}, {enabled_tex_parms=}')
        enabled_tex_parms_dict = MaterialProcessor.convert_parm_list_to_dict(enabled_tex_parms)
        textures_dict          = MaterialProcessor.get_texture_maps_from_parms(enabled_tex_parms_dict)
        textures_dict_normalized = MaterialProcessor.normalize_texture_map_keys(textures_dict)

        if convert_to == 'mtlx':
            new_shader  = Convert.convert_to_mtlx(input_node, mat_context, textures_dict_normalized)
        if convert_to == 'arnold':
            new_shader  = Convert.convert_to_arnold(input_node, mat_context, textures_dict_normalized)
        if convert_to == 'preview':
            new_shader  = Convert.convert_to_usdpreview(input_node, mat_context, textures_dict_normalized)

        # print(f'{mtlx_subnet=}')





def test():
    selected_node = hou.selectedNodes()[0] if hou.selectedNodes() else None
    if not selected_node:
        raise Exception("Please select a node.")
    traverse_class = Traverse_Node_Connections()
    traverse_tree  = traverse_class.traverse_children_nodes(selected_node)

    target_node = hou.node('/mat/arnold_materialbuilder1')
    all_connections = traverse_class.map_all_nodes_to_target_input_index(traverse_tree, node_b_type='arnold::standard_surface')
    filtered_dict = {k: v for k, v in all_connections.items() if k.type().name() == 'arnold::image'}
    print(f"\n{filtered_dict=}\n")
    mapped_nodes_dict = traverse_class.map_connection_input_index_to_texture_type(input_dict=filtered_dict)
    """
    now we have a standardized tex_node dictionary {'normal':texture_node}, we can input those into the convert class to create 
    new material. sadly the connect_<renderer>_textures() functions are using an old dictionary which has the textures
    file paths strings which we currently dont have.
    maybe I need a new function after 'map_connection_input_index_to_texture_type()' which will take all
    hou.node() items in dict and get their unExpandedString() in the same dict or another dict.
    dict1 is standardized tex_node  dictionary,
    dict2 is standardized tex_paths dictionary, now lets create it!
    
    """
    mat_context = hou.node('/mat')
    new_shader = Convert.create_arnold_shader(mat_context, 'X')
    Convert.connect_arnold_textures(new_shader, mapped_nodes_dict)





