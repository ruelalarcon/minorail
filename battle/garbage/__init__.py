from battle.garbage.base import GarbageApplication, GarbageExchange, GarbageRules
from battle.garbage.generic import GenericGarbageRules

GARBAGE_RULES = {
    "generic": GenericGarbageRules,
}

__all__ = [
    "GARBAGE_RULES",
    "GarbageApplication",
    "GarbageExchange",
    "GarbageRules",
    "GenericGarbageRules",
]
