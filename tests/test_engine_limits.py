import unittest

from runner.limits import EngineLimits, engine_limits


class EngineLimitsTests(unittest.TestCase):
    def test_missing_limits_default_to_none(self) -> None:
        self.assertEqual(engine_limits({}), EngineLimits())

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
            engine_limits(settings),
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
            engine_limits(settings, piece_limit=10, time_limit_ms=50),
            EngineLimits(piece_limit=10, time_limit_ms=50),
        )

    def test_limits_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            engine_limits({"engine": {"limits": {"piece_limit": 0}}})
        with self.assertRaises(ValueError):
            engine_limits({"engine": {"limits": {"time_limit_ms": 0}}})


if __name__ == "__main__":
    unittest.main()
