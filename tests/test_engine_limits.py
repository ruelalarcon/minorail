import unittest

from config import EngineLimits, Settings


class EngineLimitsTests(unittest.TestCase):
    def test_missing_limits_default_to_none(self) -> None:
        self.assertEqual(Settings.from_values({}).engine_limits(), EngineLimits())

    def test_settings_limits_are_used(self) -> None:
        settings = {
            "engine": {
                "limits": {
                    "piece_limit": 100,
                    "time_limit_ms": 5000,
                }
            }
        }

        self.assertEqual(
            Settings.from_values(settings).engine_limits(),
            EngineLimits(piece_limit=100, time_limit_ms=5000),
        )

    def test_overrides_win_over_settings(self) -> None:
        settings = {
            "engine": {
                "limits": {
                    "piece_limit": 100,
                    "time_limit_ms": 5000,
                }
            }
        }

        self.assertEqual(
            Settings.from_values(settings).engine_limits(
                piece_limit=10,
                time_limit_ms=50,
            ),
            EngineLimits(piece_limit=10, time_limit_ms=50),
        )

    def test_limits_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            Settings.from_values(
                {"engine": {"limits": {"piece_limit": 0}}}
            ).engine_limits()
        with self.assertRaises(ValueError):
            Settings.from_values(
                {"engine": {"limits": {"time_limit_ms": 0}}}
            ).engine_limits()


if __name__ == "__main__":
    unittest.main()
