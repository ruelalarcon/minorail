from enum import Enum


class SuggestionStatus(Enum):
    Synced = "synced"
    Advanced = "advanced"
    Resynced = "resynced"
    Invalid = "invalid"
    NoSuggestion = "no_suggestion"
