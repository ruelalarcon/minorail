from enum import Enum


class Rotation(Enum):
    North = "north"
    East = "east"
    South = "south"
    West = "west"


def rotate_cell(rotation: Rotation, x: int, y: int) -> tuple[int, int]:
    match rotation:
        case Rotation.North:
            return (x, y)
        case Rotation.East:
            return (y, -x)
        case Rotation.South:
            return (-x, -y)
        case Rotation.West:
            return (-y, x)


def rot_cw(r: Rotation) -> Rotation:
    match r:
        case Rotation.North:
            return Rotation.East
        case Rotation.East:
            return Rotation.South
        case Rotation.South:
            return Rotation.West
        case Rotation.West:
            return Rotation.North


def rot_ccw(r: Rotation) -> Rotation:
    match r:
        case Rotation.North:
            return Rotation.West
        case Rotation.West:
            return Rotation.South
        case Rotation.South:
            return Rotation.East
        case Rotation.East:
            return Rotation.North
