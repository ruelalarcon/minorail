from battle.attack.base import AttackCalculator, AttackResult
from battle.attack.generic import GenericAttackCalculator

ATTACK_CALCULATORS = {
    "generic": GenericAttackCalculator,
}

__all__ = [
    "ATTACK_CALCULATORS",
    "AttackCalculator",
    "AttackResult",
    "GenericAttackCalculator",
]
