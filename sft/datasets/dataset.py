import torch
import os
from typing import Dict
from pathlib import Path
import numpy as np
import trimesh
import open3d as o3d

SYNSET_DICT_DIR = Path(__file__).resolve().parent  

def sample_pc(verts, faces, pc_num, with_normal=False):
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    if not with_normal:
        points, _ = mesh.sample(pc_num, return_index=True)
        return points
    points, face_idx = mesh.sample(50000, return_index=True)
    normals = mesh.face_normals[face_idx]
    pc_normal = np.concatenate([points[:,[2,0,1]], normals[:,[2,0,1]]], axis=-1, dtype=np.float16)
    # random sample point cloud
    ind = np.random.choice(pc_normal.shape[0], pc_num, replace=False)
    pc_normal = pc_normal[ind]
    return pc_normal

class Sample_Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        quant_bit: int     = 9,
        point_num:int      = 16384,
        path:str           = "",
        uid_list:list      = []
    ) -> None:
        super().__init__()
        self.quant_bit    = quant_bit
        self.point_num    = point_num
        self.path         = path
        name              = os.listdir(path)
        if uid_list == [""]:
            self.uid_list     = [i for i in name if len(i.split("."))>1]
        else:
            self.uid_list    = uid_list
    
    def __len__(self) -> int:
        return len(self.uid_list)

    def __getitem__(self, idx: int) -> Dict:
        data = {}
        data_path = f"{self.path}/{self.uid_list[idx]}"
        if self.uid_list[idx].split(".")[-1] == "obj":
            mesh         = trimesh.load(data_path)
            verts, faces = mesh.vertices,mesh.faces
            indices      = np.random.choice(50000, self.point_num, replace=False)
            pc_normal    = sample_pc(verts, faces, pc_num=50000, with_normal=True)[indices]
        elif self.uid_list[idx].split(".")[-1] == "ply":
            pc_path = data_path
            points = trimesh.load(pc_path, process=False)
    
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=30))
            pcd.orient_normals_consistent_tangent_plane(k=30)
            points = np.asarray(pcd.points)
            normals = np.asarray(pcd.normals)
            pc_normal = np.concatenate([points, normals], axis=1)
            
            if len(pc_normal)>self.point_num:
                indices   = np.random.choice(len(pc_normal), self.point_num, replace=False)
                pc_normal     = pc_normal[indices]
        data['pc_normal'] = torch.tensor(pc_normal)
        data['path'] = data_path
        return data
