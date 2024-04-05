import hou
from nodesearch import parser, NodeType
    

def find_nodes(node_name='filecache', parent=hou.node("/obj"), use_recursive=False) -> list:
    """
    finds all nodes with specific name inside a parent. you can use '*' symbol'
    """
    found_nodes = []
    matcher = parser.parse_query(node_name)
    temp    = matcher.nodes(parent, recursive=use_recursive, recurse_in_locked_nodes=False)
    found_nodes.extend(temp)
    return found_nodes

def get_all_bypassed_nodes(parent_node = hou.node("/obj")) -> list:
    bypassed_nodes_list = []
    for node in parent_node.allSubChildren(recurse_in_locked_nodes=False):
        if node.type().category().name() == 'Sop':
            if node.isBypassed():
                bypassed_nodes_list.extend(node)
    return bypassed_nodes_list

def delete_nodes(nodes_list: list) -> None:
    for node in nodes_list:
        node.destroy()

def button_parameter_press(input_nodes: list, parm_to_press='execute') -> None:
    """
    input -> list of hou.node(),
    process: presses a button, can be used to cache multiple file caches,
    output <- None
    """
    try:
        for file_node in input_nodes:      
            file_node.parm(parm_to_press).pressButton()
    except:
        raise Exception(f"Exception raised while trying to press '{parm_to_press}' button. possibly the function was trying to cache a non filecache node ")

def get_parameter(input_nodes: list, parm_name='file'):
    parm_list = []
    for node in input_nodes:
        parm      = node.parm(parm_name)
        parm_list.append(parm)
    # print(f'{parm_list=}')
    return parm_list

def modify_str_parameter(input_parm: list, oldvalue='', newvalue='') -> None:
    for parm in input_parm:
        parm_str  = parm.unexpandedString()
        new_string = parm_str.replace('$HIP', '$CACHE')
        # print(f'{new_string=}')
        parm.set(new_string)
############################################################################








################ FUNCTIONS SPECIFIC TO CACHING THE FEATHERS ################

def find_feather_anim_cache() -> list:
    find_feather_anim_cache = find_nodes(node_name='*_deform')
    found_nodes = []
    for geo_node in find_feather_anim_cache:
        temp = find_nodes(node_name='*FEATHER_ANIM_CACHE', parent = geo_node)
        found_nodes.extend(temp)
        # print(f'find_feather_anim_cache()-----{temp}')
    return found_nodes

def change_cache_location(oldvalue='$HIP', newvalue='$CACHE') -> None:
    filecache_nodes      = find_feather_anim_cache()
    file_cache_parm_file = get_parameter(filecache_nodes, parm_name='file')
    modify_str_parameter(file_cache_parm_file, oldvalue=oldvalue, newvalue=newvalue)


def cache_eagle_shot() -> None:
    """
    input <- bunch of filecache nodes which will be cached
    process: caches all filecache nodes one by one
    output -> None
    """    
    file_caches_nodes = find_feather_anim_cache()
    file_caches_nodes.append(hou.node('/obj/small_hair/hair_ANIM_CACHE'))
    file_caches_nodes.append(hou.node('/obj/small_hair_02/FEATHER_ANIM_CACHE'))

    button_parameter_press(file_caches_nodes)
    print(f'///////////// DONE ///////////// \n\n')

def clean_scene_from_FC_nodes() -> None:
    Kamal_fgenearter_nodes_list = find_nodes(node_name='*Kamal_fgenearter', parent = obj, use_recursive=True)
    FDeform_nodes_list          = find_nodes(node_name='FDeform'          , parent = obj, use_recursive=True)
    # print(f'{Kamal_fgenearter_nodes_list=}')
    # print(f'{FDeform_nodes_list=}')
    delete_nodes(Kamal_fgenearter_nodes_list)
    delete_nodes(FDeform_nodes_list)


###################################

geo_node    = NodeType("geo")
obj         = hou.node("/obj")


change_cache_location()
# modify_str_parameter(filecache_nodes)
# cache_eagle_shot()
# clean_scene_from_FC_nodes()