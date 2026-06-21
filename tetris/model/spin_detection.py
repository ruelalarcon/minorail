from enum import StrEnum


class SpinDetection(StrEnum):
    none = "none"
    t_spins = "t-spins"
    t_spins_plus = "t-spins+"
    all = "all"
    all_plus = "all+"
    all_mini = "all-mini"
    all_mini_plus = "all-mini+"
    mini_only = "mini-only"
