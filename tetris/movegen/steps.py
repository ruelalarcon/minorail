from enum import Enum


class MoveStep(Enum):
    Left = "left"
    Right = "right"
    DasLeft = "das_left"
    DasRight = "das_right"
    RotCW = "rot_cw"
    RotCCW = "rot_ccw"
    Rot180 = "rot_180"
    SoftDrop = "soft_drop"
    SonicDrop = "sonic_drop"
    HardDrop = "hard_drop"
