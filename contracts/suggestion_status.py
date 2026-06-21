from enum import Enum


class SuggestionStatus(Enum):
    Synced = "synced"
    Advanced = "advanced"
    Reconciled = "reconciled"
    Reset = "reset"
    Invalid = "invalid"
    NoSuggestion = "no_suggestion"
