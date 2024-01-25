import numpy as np
import argparse
from tqdm import tqdm
import matplotlib.pyplot as plt
import torch

from configs.default import get_cfg_defaults
from datasets import dataset_dict
from RelPoseRepo.pose import PoseRecover
from utils.metrics import relative_pose_error, rotation_angular_error, error_auc


def main(args):
    config = get_cfg_defaults()
    config.merge_from_file(args.config)

    try:
        data_root = config.DATASET.TEST.DATA_ROOT
    except:
        data_root = config.DATASET.DATA_ROOT
    
    build_fn = dataset_dict[args.task][args.dataset]
    testset = build_fn('train', config)
    testloader = torch.utils.data.DataLoader(testset, batch_size=1, shuffle=True)

    device = args.device
    img_resize = (args.h_new, args.w_new) if args.resize else None
    poseRec = PoseRecover(matcher=args.matcher, solver=0, img_resize=img_resize, device=device)
    
    R_errs, t_errs = [], []
    R_gts, t_gts = [], []
    for i, data in enumerate(tqdm(testloader)):
        # if i > 10:
        #     break
        # if data['objName'][0][0] != '011_banana':
        #     continuepr
        image0, image1 = data['images'][0].to(device)

        bbox0, bbox1 = None, None
        if args.task == 'object':
            bbox0, bbox1 = data['bboxes'][0]
            x1, y1, x2, y2 = bbox0
            u1, v1, u2, v2 = bbox1
            image0 = image0[:, y1:y2, x1:x2]
            image1 = image1[:, v1:v2, u1:u2]

        mask0, mask1 = None, None
        if args.mask:
            mask0, mask1 = data['masks'][0].to(device)

        depth0, depth1 = None, None
        if args.depth:
            depth0, depth1 = data['depths'][0]

        K0, K1 = data['intrinsics'][0]
        T = torch.eye(4)
        T[:3, :3] = data['rotation'][0]
        T[:3, 3] = data['translation'][0]
        T = T.numpy()
        R, t, points0, points1 = poseRec.recover(image0, image1, K0, K1, bbox0, bbox1, mask0, mask1, depth0, depth1)
        plt.imshow(data['images'][0, 0].permute(1, 2, 0))
        plt.scatter(points0[:, 0], points0[:, 1])
        plt.show()
        plt.imshow(data['images'][0, 1].permute(1, 2, 0))
        plt.scatter(points1[:, 0], points1[:, 1])
        plt.show()
        # break
        # # R_s, t_s, points0, points1 = poseRec.recover(image0, image1, K0, K1, bbox0, bbox1, mask0, mask1)
        # pts3D0, pts3D1 = data['objCorners'][0]
        # coord_change_mat = torch.tensor([[1., 0., 0.], [0, -1., 0.], [0., 0., -1.]])
        # # if is_OpenGL_coords:
        # # pts3D_t = pts3D0 @ torch.from_numpy(R).float().mT + torch.from_numpy(t).float()
        # # pts3D_ts = pts3D0 @ torch.from_numpy(R_s).float().mT + torch.from_numpy(t_s).float()

        # pts3D0 = pts3D0 @ coord_change_mat.mT
        # pts3D1 = pts3D1 @ coord_change_mat.mT
        # # pts3D_t = pts3D_t @ coord_change_mat.mT
        # # pts3D_ts = pts3D_ts @ coord_change_mat.mT

        # proj_pts0 = pts3D0 @ K0.mT.float()
        # proj_pts1 = pts3D1 @ K1.mT.float()
        # # proj_pts_t = pts3D_t @ K0.mT.float()
        # # proj_pts_ts = pts3D_ts @ K0.mT.float()

        # proj_pts0 = torch.stack([proj_pts0[:,0]/proj_pts0[:,2], proj_pts0[:,1]/proj_pts0[:,2]],axis=1)
        # proj_pts1 = torch.stack([proj_pts1[:,0]/proj_pts1[:,2], proj_pts1[:,1]/proj_pts1[:,2]],axis=1)
        # # proj_pts_t = torch.stack([proj_pts_t[:,0]/proj_pts_t[:,2], proj_pts_t[:,1]/proj_pts_t[:,2]],axis=1)
        # # proj_pts_ts = torch.stack([proj_pts_ts[:,0]/proj_pts_ts[:,2], proj_pts_ts[:,1]/proj_pts_ts[:,2]],axis=1)
        # # import pdb
        # # pdb.set_trace()
        # print(T)
        # print(R)
        # print(t)

        # plt.subplot(1, 2, 1)
        # plt.imshow(data['images'][0, 0].permute(1, 2, 0))
        # # plt.scatter([bbox[0], bbox[2]], [bbox[1], bbox[3]])
        # plt.scatter(proj_pts0[:, 0], proj_pts0[:, 1])
        # plt.subplot(1, 2, 2)
        # plt.imshow(data['images'][0, 1].permute(1, 2, 0))
        # plt.scatter(proj_pts1[:, 0], proj_pts1[:, 1])
        # # plt.scatter(proj_pts_ts[:, 0], proj_pts_ts[:, 1])
        # # plt.scatter(proj_pts_t[:, 0], proj_pts_t[:, 1])
        # plt.show()
        # break

        if np.isnan(R).any():
            R_err = 180
            t_err = 180
        else:
            t_err, R_err = relative_pose_error(T, R, t, ignore_gt_t_thr=0.0)

        R_errs.append(R_err)
        t_errs.append(t_err)

        R_gt = rotation_angular_error(torch.from_numpy(T[:3, :3])[None], torch.eye(3)[None])
        R_gts.append(R_gt[0])
        t_gt = torch.tensor(T[:3, 3]).norm(2)
        t_gts.append(t_gt)

    # pose auc
    angular_thresholds = [5, 10, 20]
    pose_errors = np.max(np.stack([R_errs, t_errs]), axis=0)
    aucs = error_auc(pose_errors, angular_thresholds, mode=args.matcher)  # (auc@5, auc@10, auc@20)
    for k in aucs:
        print(f'{k}:\t{aucs[k]:.4f}')
    
    R_errs = torch.tensor(R_errs)
    t_errs = torch.tensor(t_errs)
    print(f'rotation_err_avg:\t{R_errs.mean():.2f}')
    print(f'rotation_err_med:\t{R_errs.median():.2f}')
    print(f'rotation_acc_30d:\t{(R_errs < 30).float().mean():.4f}')
    print(f'translation_err_avg:\t{t_errs.mean():.2f}')
    print(f'translation_err_med:\t{t_errs.median():.2f}')
    
    R_gts = torch.tensor(R_gts).rad2deg()
    t_gts = torch.tensor(t_gts)
    print(f'rel_rotation_avg:\t{R_gts.mean():.2f}')
    print(f'rel_rotation_max:\t{R_gts.max():.2f}')
    print(f'rel_translation_avg:\t{t_gts.mean():.2f}')
    print(f'rel_translation_max:\t{t_gts.max():.2f}')


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--task', type=str, help='scene | object', choices={'scene', 'object'}, required=True)
    parser.add_argument('--dataset', type=str, help='matterport | megadepth | scannet | bop', required=True)
    parser.add_argument('--config', type=str, help='.yaml configure file path', required=True)

    parser.add_argument('--matcher', type=str, required=True)
    parser.add_argument('--device', type=str, default='cuda:0')

    parser.add_argument('--resize', action='store_true')
    parser.add_argument('-w_new', type=int, default=640)
    parser.add_argument('-h_new', type=int, default=480)
    parser.add_argument('--mask', action='store_true')
    parser.add_argument('--depth', action='store_true')

    return parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)