import os
import hou
import re

def getFootage(kwargs):
    # V:/ElNashashen/Footage/Eps_03/SC_22A/Raw/Shot_184/v02/
    filters            = (".jpg",".jpeg")

    node               = kwargs['node']
    case               = ["series","movie"]
    choose             = case[int(node.parm('projectType').eval())]
    project_name       = str(node.parm('projects').eval()).split("_VFX")[0]
    selected_sec_name  = node.parm('scene').eval()
    selected_shot_name = node.parm('shot').eval()
    try:
        footage_dir = 'Y:/{}/Footage/'.format(project_name)


        eps_list  = []
        seq_list  = []
        eps_dir   = None


        if choose == "series":
            if os.path.exists(footage_dir):
                eps     = os.listdir(footage_dir)
                if eps:
                  eps_list = eps




        version_dirs_list = []
        if eps_list:
           for ep in eps_list:
            #    eps_dir   = "{}{}/".format(footage_dir, ep)
                eps_dir   = f"{footage_dir}{ep}/"
                selected_eps_name = selected_sec_name.split("_")[1]
                find_eps_num  = re.search(r'\d+',ep)
                if find_eps_num:
                  if int(selected_eps_name) == int(find_eps_num.group()):
                       if os.path.isdir(eps_dir):
                         for seq in os.listdir(eps_dir):
                            current_seq     = selected_sec_name.split("_")[-1]          # shouldnt be in a loop
                            current_seq_num = re.search(r'\d+',current_seq).group()
                            find_seq_num    = re.search(r'\d+',seq)
                            if find_seq_num:
                                if int(current_seq_num) ==int(find_seq_num.group()): 
                                    sequence_full_path = str(eps_dir + seq + "/raw/") 
                                    current_shot_name = selected_shot_name.split('_')(-1)
                                    try:
                                        for shot in os.listdir(sequence_full_path):
                                            if int(current_shot_name) == int(shot.split("_")[-1]):
                                                full_shot_dir = str(sequence_full_path + shot)
                                                for version in os.listdir(full_shot_dir):
                                                    full_footage_version_path ="{}/{}".format(full_shot_dir.replace("\\","/"),version)
                                                    if not os.path.isfile(full_footage_version_path):
                                                        if full_footage_version_path not in version_dirs_list:
                                                            version_dirs_list.append(full_footage_version_path)
                                                            version_dirs_list.append(version)

                                    except:
                                        print(f'sequence_full_path is empty,: {sequence_full_path}')


        return version_dirs_list

    except:
        return ["INVALID PATH", "INVALID PATH"]








def getEpsList(kwargs, choose='series', footage_dir=''):
    eps_list  = []
    seq_list  = []
    eps_dir   = None

    if choose == "series":
        if os.path.exists(footage_dir):
            eps     = os.listdir(footage_dir)
            if eps:
                eps_list = eps
    








varList: [
    'projectType',
    'projects',
    'scene',
    'shot',
    'project_name',
    'footage_dir',
    'eps_list',
    'seq_list',
    'eps_dir',
    'selected_sec_name',
    'version_dirs_list',
    'selected_eps_name',
    'find_eps_num',
    'current_seq',
    'current_seq_num',
    'find_seq_num',
    'sequence_full_path',
    'selected_shot_name',
    'current_shot_name',
    'full_footage_version_path',
    'full_shot_dir',
    'version',
    'filters',
    ]
