"""
copyright Ahmed Hindy. please mention the original author if you used any part of this code
"""

import hou
from typing import Dict
from pprint import pprint


class MaterialProcessor():
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
    def get_texture_parms_from_principled_shader(input_node) -> Dict[str, hou.parm]:
        """
        input  -> hou.node() of type 'principledshader::2.0'
        process: returns dict of parameters on a node that have '<tex_name>_useTexture' enabled
                 basically get all enabled texture parameters.
        output <- dictionary containing all enabled texture parameters on the principled shader.
                  e.g. {'basecolor_texture': <hou.Parm basecolor_texture in /mat/principledshader2>}
        """
        input_tex_parm_dict ={}
        for parm in input_node.parms():
            if '_useTexture' in parm.name():
                if parm.eval() == 1:
                    input_tex_str  = parm.name().split('_useTexture')[0] + '_texture'
                    input_tex_parm = input_node.parm(input_tex_str)
                    # print(f'{input_tex_parm=}')
                    input_tex_parm_dict[input_tex_str] = input_tex_parm

        # special case for getting displacement
        if input_node.parm('dispTex_enable'):
            input_tex_str = 'displacement' + '_texture'
            input_tex_parm = input_node.parm('dispTex_texture')
            input_tex_parm_dict[input_tex_str] = input_tex_parm

        print(f'{input_tex_parm_dict=}')
        return input_tex_parm_dict

    @staticmethod
    def get_texture_parms_from_arnold_shader(input_node) -> Dict[str, hou.parm]:
        """
        input  -> hou.node() of type 'arnold_materialbuilder'
        process: returns dict of parameters on nodes 'arnold::image' that are connected to the shader
        output <- dictionary containing all enabled texture parameters on the principled shader.
                  e.g. {'basecolor_texture': <hou.Parm basecolor_texture in /mat/principledshader2>}
        """
        input_tex_parm_dict ={}
        for parm in input_node.parms():
            if '_useTexture' in parm.name():
                if parm.eval() == 1:
                    input_tex_str  = parm.name().split('_useTexture')[0] + '_texture'
                    input_tex_parm = input_node.parm(input_tex_str)
                    # print(f'{input_tex_parm=}')
                    input_tex_parm_dict[input_tex_str] = input_tex_parm

        # special case for getting displacement
        if input_node.parm('dispTex_enable'):
            input_tex_str = 'displacement' + '_texture'
            input_tex_parm = input_node.parm('dispTex_texture')
            input_tex_parm_dict[input_tex_str] = input_tex_parm

        print(f'{input_tex_parm_dict=}')
        return input_tex_parm_dict

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

        print(f'{textures_dict=}')
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
                print(f'/// {key=} is {value=}')
                normalized_dict[key] = value

        return normalized_dict


# class NotUsed():
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
        for input_index, input_node in enumerate(node.inputs()):
            if input_node is not None:
                # Recursively traverse the input node, building the dictionary
                input_node_dict = self.traverse_node_tree(input_node, path + [node])
                node_dict[node].update(input_node_dict)

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
        ### Identify nodes that are not inputs to any other node. if no output detected then is_output=True
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
            ### Build and add the branch dictionary for each output node
            branch_dict = self.traverse_node_tree(output_node, [])
            all_branches.update(branch_dict)

        return all_branches

    @staticmethod
    def find_nodes_of_type(node_dict, node_type, found_nodes=None):
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




class Convert():
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
    def create_arnold_shader(mat_context, node_name=''):
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
            print(f'{key=} , {value=}')
            tex = arnold_subnet.node(key)
            if tex:
                tex.parm("filename").set(value)
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
        enabled_tex_parms = MaterialProcessor.get_texture_parms_from_principled_shader(input_node)
        # print(f'{input_node=}, {enabled_tex_parms=}')
        textures_dict     = MaterialProcessor.get_texture_maps_from_parms(enabled_tex_parms)
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
    node_tree_dict = traverse_class.traverse_children_nodes(selected_node)
    found_nodes    = traverse_class.find_nodes_of_type(node_dict=node_tree_dict, node_type='arnold::image')

    pprint(found_nodes)
