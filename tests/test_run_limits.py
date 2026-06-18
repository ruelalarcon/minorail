import unittest

from settings import RunLimits, Settings


class RunLimitsTests(unittest.TestCase):
    def test_missing_limits_default_to_none(self) -> None:
        self.assertEqual(Settings.from_values({}).run_limits(), RunLimits())

    def test_settings_limits_are_used(self) -> None:
        settings = {
            "game": {
                "limits": {
                    "piece_limit": 100,
                    "time_limit_ms": 5000,
                }
            }
        }

        self.assertEqual(
            Settings.from_values(settings).run_limits(),
            RunLimits(piece_limit=100, time_limit_ms=5000),
        )

    def test_overrides_win_over_settings(self) -> None:
        settings = {
            "game": {
                "limits": {
                    "piece_limit": 100,
                    "time_limit_ms": 5000,
                }
            }
        }

        self.assertEqual(
            Settings.from_values(settings).run_limits(
                piece_limit=10,
                time_limit_ms=50,
            ),
            RunLimits(piece_limit=10, time_limit_ms=50),
        )

    def test_limits_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            Settings.from_values({"game": {"limits": {"piece_limit": 0}}}).run_limits()
        with self.assertRaises(ValueError):
            Settings.from_values(
                {"game": {"limits": {"time_limit_ms": 0}}}
            ).run_limits()


if __name__ == "__main__":
    unittest.main()
