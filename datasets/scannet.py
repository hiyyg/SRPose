from os import path as osp
import numpy as np
from numpy.linalg import inv
import cv2
from tqdm import tqdm

import torch
from torch.utils.data import Dataset, ConcatDataset

from utils import Augmentor


def read_scannet_pose(path):
    """ Read ScanNet's Camera2World pose and transform it to World2Camera.
    
    Returns:
        pose_w2c (np.ndarray): (4, 4)
    """
    cam2world = np.loadtxt(path, delimiter=' ')
    world2cam = inv(cam2world)
    return world2cam


class ScanNetDataset(Dataset):
    def __init__(self,
                 root_dir,
                 npz_path,
                 intrinsic_path,
                 mode='train',
                 min_overlap_score=0.4,
                #  augment_fn=None,
                 pose_dir=None,
                #  **kwargs
                 ):
        """Manage one scene of ScanNet Dataset.
        Args:
            root_dir (str): ScanNet root directory that contains scene folders.
            npz_path (str): {scene_id}.npz path. This contains image pair information of a scene.
            intrinsic_path (str): path to depth-camera intrinsic file.
            mode (str): options are ['train', 'val', 'test'].
            augment_fn (callable, optional): augments images with pre-defined visual effects.
            pose_dir (str): ScanNet root directory that contains all poses.
                (we use a separate (optional) pose_dir since we store images and poses separately.)
        """
        super().__init__()
        self.root_dir = root_dir
        self.pose_dir = pose_dir if pose_dir is not None else root_dir
        self.mode = mode

        # prepare data_names, intrinsics and extrinsics(T)
        with np.load(npz_path) as data:
            self.data_names = data['name']
            if 'score' in data.keys() and mode not in ['val' or 'test']:
                kept_mask = data['score'] > min_overlap_score
                self.data_names = self.data_names[kept_mask]
        self.intrinsics = dict(np.load(intrinsic_path))

        # # for training LoFTR
        # self.augment_fn = augment_fn if mode == 'train' else None
        self.augment = Augmentor(mode=='train')

    def __len__(self):
        return len(self.data_names)

    def _read_abs_pose(self, scene_name, name):
        pth = osp.join(self.pose_dir,
                       scene_name,
                       'pose', f'{name}.txt')
        return read_scannet_pose(pth)

    def _compute_rel_pose(self, scene_name, name0, name1):
        pose0 = self._read_abs_pose(scene_name, name0)
        pose1 = self._read_abs_pose(scene_name, name1)
        
        return np.matmul(pose1, inv(pose0))  # (4, 4)

    def __getitem__(self, idx):
        data_name = self.data_names[idx]
        scene_name, scene_sub_name, stem_name_0, stem_name_1 = data_name
        scene_name = f'scene{scene_name:04d}_{scene_sub_name:02d}'

        # read the grayscale image which will be resized to (1, 480, 640)
        img_name0 = osp.join(self.root_dir, scene_name, 'color', f'{stem_name_0}.jpg')
        img_name1 = osp.join(self.root_dir, scene_name, 'color', f'{stem_name_1}.jpg')
        
        # image0 = read_scannet_gray(img_name0, resize=(640, 480), augment_fn=None)
        #                         #    augment_fn=np.random.choice([self.augment_fn, None], p=[0.5, 0.5]))
        # image1 = read_scannet_gray(img_name1, resize=(640, 480), augment_fn=None)
        #                         #    augment_fn=np.random.choice([self.augment_fn, None], p=[0.5, 0.5]))

        w_new, h_new = 640, 480

        image0 = cv2.imread(img_name0)
        image0 = cv2.resize(image0, (w_new, h_new))
        image0 = cv2.cvtColor(image0, cv2.COLOR_BGR2RGB)
        # image0 = self.augment(image0)
        image0 = torch.from_numpy(image0).permute(2, 0, 1).float() / 255.

        image1 = cv2.imread(img_name1)
        image1 = cv2.resize(image1, (w_new, h_new))
        image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2RGB)
        # image1 = self.augment(image1)
        image1 = torch.from_numpy(image1).permute(2, 0, 1).float() / 255.
        images = torch.stack([image0, image1], dim=0)

        depth0 = cv2.imread(osp.join(self.root_dir, scene_name, 'depth', f'{stem_name_0}.png'), cv2.IMREAD_UNCHANGED)
        depth0 = depth0 / 1000
        depth0 = torch.from_numpy(depth0).float()

        depth1 = cv2.imread(osp.join(self.root_dir, scene_name, 'depth', f'{stem_name_1}.png'), cv2.IMREAD_UNCHANGED)
        depth1 = depth1 / 1000
        depth1 = torch.from_numpy(depth1).float()
        depths = torch.stack([depth0, depth1], dim=0)

        # # read the depthmap which is stored as (480, 640)
        # if self.mode in ['train', 'val']:
        #     depth0 = read_scannet_depth(osp.join(self.root_dir, scene_name, 'depth', f'{stem_name_0}.png'))
        #     depth1 = read_scannet_depth(osp.join(self.root_dir, scene_name, 'depth', f'{stem_name_1}.png'))
        # else:
        #     depth0 = depth1 = torch.tensor([])

        # read the intrinsic of depthmap
        K_0 = K_1 = torch.tensor(self.intrinsics[scene_name].copy(), dtype=torch.float).reshape(3, 3)
        intrinsics = torch.stack([K_0, K_1], dim=0)

        # read and compute relative poses
        T_0to1 = torch.tensor(self._compute_rel_pose(scene_name, stem_name_0, stem_name_1),
                              dtype=torch.float32)
        # T_1to0 = T_0to1.inverse()

        # data = {
        #     'image0': image0,   # (3, h, w)
        #     # 'depth0': depth0,   # (h, w)
        #     'image1': image1,
        #     # 'depth1': depth1,
        #     'T_0to1': T_0to1,   # (4, 4)
        #     # 'T_1to0': T_1to0,
        #     'K0': K_0,  # (3, 3)
        #     'K1': K_1,
        #     'dataset_name': 'ScanNet',
        #     'scene_id': scene_name,
        #     'pair_id': idx,
        #     'pair_names': (osp.join(scene_name, 'color', f'{stem_name_0}.jpg'),
        #                    osp.join(scene_name, 'color', f'{stem_name_1}.jpg'))
        # }

        data = {
            'images': images,
            'depths': depths,
            'rotation': T_0to1[:3, :3],
            'translation': T_0to1[:3, 3],
            'intrinsics': intrinsics,
            'pair_names': (osp.join(scene_name, 'color', f'{stem_name_0}.jpg'),
                           osp.join(scene_name, 'color', f'{stem_name_1}.jpg'))
        }

        return data
    

def build_concat_scannet(mode, config):
    if mode == 'train':
        config = config.DATASET.TRAIN
    elif mode == 'val':
        config = config.DATASET.VAL
    elif mode == 'test':
        config = config.DATASET.TEST
    else:
        raise NotImplementedError(f'mode {mode}')

    data_root = config.DATA_ROOT
    # pose_root = config.POSE_ROOT
    npz_root = config.NPZ_ROOT
    list_path = config.LIST_PATH
    intrinsic_path = config.INTRINSIC_PATH
    min_overlap_score = config.MIN_OVERLAP_SCORE

    with open(list_path, 'r') as f:
        npz_names = [name.split()[0] for name in f.readlines()]

    datasets = []
    # npz_names = [f'{n}.npz' for n in npz_names]
    for npz_name in tqdm(npz_names, desc=f'Loading ScanNet {mode} datasets',):
        npz_path = osp.join(npz_root, npz_name)
        datasets.append(ScanNetDataset(
            data_root,
            npz_path,
            intrinsic_path,
            mode=mode,
            min_overlap_score=min_overlap_score,
            # augment_fn=augment_fn,
            # pose_dir=pose_dir
        ))

    return ConcatDataset(datasets)

