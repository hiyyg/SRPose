import argparse
import numpy as np
import torch

from lightglue import SuperPoint, LightGlue
from lightglue.utils import rbd
from kornia.feature import LoFTR

from utils import compute_pose_errors, error_auc
from datasets import dataset_dict
from configs.default import get_cfg_defaults


def main(args):
    config = get_cfg_defaults()
    config.merge_from_file(args.config)

    # seed = config.RANDOM_SEED
    # seed_torch(seed)
    
    build_fn = dataset_dict[args.task][args.dataset]
    testset = build_fn('test', config)
    # testloader = DataLoader(testset, batch_size=batch_size, num_workers=num_workers, pin_memory=pin_memory)

    # SuperPoint+LightGlue
    extractor = SuperPoint(max_num_keypoints=2048).eval().cuda()  # load the extractor
    matcher = LightGlue(features='superpoint').eval().cuda()  # load the matcher

    R_errs = []
    t_errs = []
    for data in testset:
        # load each image as a torch.Tensor on GPU with shape (3,H,W), normalized in [0,1]
        image0, image1 = data['images']
        K0, K1 = data['intrinsics']
        T = torch.eyes(4)
        T[:3, :3] = data['rotation']
        T[:3, 3] = data['translation']

        # extract local features
        feats0 = extractor.extract(image0)  # auto-resize the image, disable with resize=None
        feats1 = extractor.extract(image1)

        # match the features
        matches01 = matcher({'image0': feats0, 'image1': feats1})
        feats0, feats1, matches01 = [rbd(x) for x in [feats0, feats1, matches01]]  # remove batch dimension
        matches = matches01['matches']  # indices with shape (K,2)
        points0 = feats0['keypoints'][matches[..., 0]]  # coordinates in image #0, shape (K,2)
        points1 = feats1['keypoints'][matches[..., 1]]  # coordinates in image #1, shape (K,2)

        R_err, t_err, _ = compute_pose_errors(points0, points1, K0, K1, T)
        R_errs.append(R_err)
        t_errs.append(t_errs)

    # pose auc
    angular_thresholds = [5, 10, 20]
    pose_errors = np.max(np.stack([R_errs, t_errs]), axis=0)
    aucs = error_auc(pose_errors, angular_thresholds)  # (auc@5, auc@10, auc@20)

    print(aucs)
    

def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--task', type=str, help='scene | object', required=True)
    parser.add_argument('--dataset', type=str, help='matterport | megadepth | scannet | bop', required=True)
    # parser.add_argument('--config', type=str, help='.yaml configure file path', required=True)
    # parser.add_argument('--resume', type=str, required=True)
    # parser.add_argument('--method', type=str, help='superglue | lightglue | loftr', required=True)

    # parser.add_argument('--world_size', type=int, default=2)
    # parser.add_argument('--device', type=str, default='cuda:0')

    return parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)
