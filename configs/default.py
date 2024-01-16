from yacs.config import CfgNode as CN


_CN = CN()

# Model
_CN.MODEL = CN()
_CN.MODEL.NUM_KEYPOINTS = 1024
_CN.MODEL.TEST_NUM_KEYPOINTS = 1024
_CN.MODEL.N_LAYERS = 6
_CN.MODEL.NUM_HEADS = 4

# Dataset
_CN.DATASET = CN()
_CN.DATASET.DATA_SOURCE = None
_CN.DATASET.DATA_ROOT = None
_CN.DATASET.MIN_OVERLAP_SCORE = None

## For Linemod(BOP)
_CN.DATASET.OBJECT_ID = None
_CN.DATASET.MIN_VISIBLE_FRACT = None
_CN.DATASET.MAX_ANGLE_ERROR = None
_CN.DATASET.JSON_PATH = None

## For MegaDepth/ScanNet
_CN.DATASET.TRAIN = CN()
_CN.DATASET.TRAIN.DATA_ROOT = None
_CN.DATASET.TRAIN.NPZ_ROOT = None
_CN.DATASET.TRAIN.LIST_PATH = None
_CN.DATASET.TRAIN.INTRINSIC_PATH = None
_CN.DATASET.TRAIN.MIN_OVERLAP_SCORE = None

_CN.DATASET.VAL = CN()
_CN.DATASET.VAL.DATA_ROOT = None
_CN.DATASET.VAL.NPZ_ROOT = None
_CN.DATASET.VAL.LIST_PATH = None
_CN.DATASET.VAL.INTRINSIC_PATH = None
_CN.DATASET.VAL.MIN_OVERLAP_SCORE = None

_CN.DATASET.TEST = CN()
_CN.DATASET.TEST.DATA_ROOT = None
_CN.DATASET.TEST.NPZ_ROOT = None
_CN.DATASET.TEST.LIST_PATH = None
_CN.DATASET.TEST.INTRINSIC_PATH = None
_CN.DATASET.TEST.MIN_OVERLAP_SCORE = None

# Train
_CN.TRAINER = CN()
# _CN.TRAINER.WORLD_SIZE = 1
# _CN.TRAINER.MASTER_PORT = 12355
# _CN.TRAINER.DEVICE = 'cuda:0'

_CN.TRAINER.EPOCHS = None
_CN.TRAINER.LEARNING_RATE = None
_CN.TRAINER.PCT_START = None
_CN.TRAINER.BATCH_SIZE = None
_CN.TRAINER.NUM_WORKERS = None
_CN.TRAINER.PIN_MEMORY = True
_CN.TRAINER.N_SAMPLES_PER_SUBSET = None

_CN.TRAINER.SAVE_PATH = './checkpoints'
_CN.RANDOM_SEED = 0


_CN.EMAT_RANSAC = CN()
_CN.EMAT_RANSAC.PIX_THRESHOLD = 0.5
_CN.EMAT_RANSAC.SCALE_THRESHOLD = 0.1
_CN.EMAT_RANSAC.CONFIDENCE = 0.99999

_CN.PNP = CN()
_CN.PNP.RANSAC_ITER = 1000
_CN.PNP.REPROJECTION_INLIER_THRESHOLD = 3
_CN.PNP.CONFIDENCE = 0.99999

_CN.PROCRUSTES = CN()
_CN.PROCRUSTES.MAX_CORR_DIST = 0.05 # meters
_CN.PROCRUSTES.REFINE = False


def get_cfg_defaults():
    """Get a yacs CfgNode object with default values for my_project."""
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return _CN.clone()
