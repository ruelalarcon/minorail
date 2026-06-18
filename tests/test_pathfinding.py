import unittest

from settings import PathSettings, Settings


class PathSettingsTests(unittest.TestCase):
    def test_missing_setting_uses_consumer_default(self) -> None:
        settings = {"service": {"path": {}}}

        self.assertTrue(
            Settings.from_values(settings)
            .pathfinding(default_pathfinding=True)
            .pathfinding
        )
        self.assertFalse(
            Settings.from_values(settings)
            .pathfinding(default_pathfinding=False)
            .pathfinding
        )

    def test_settings_value_overrides_consumer_default(self) -> None:
        self.assertTrue(
            Settings.from_values({"service": {"path": {"pathfinding": True}}})
            .pathfinding(default_pathfinding=False)
            .pathfinding
        )
        self.assertFalse(
            Settings.from_values({"service": {"path": {"pathfinding": False}}})
            .pathfinding(default_pathfinding=True)
            .pathfinding
        )

    def test_cli_override_wins_over_settings(self) -> None:
        settings = {"service": {"path": {"pathfinding": False}}}

        self.assertTrue(
            Settings.from_values(settings)
            .pathfinding(default_pathfinding=False, pathfinding=True)
            .pathfinding
        )

    def test_conversion_is_inert_without_pathfinding(self) -> None:
        path_settings = Settings.from_values(
            {
                "service": {
                    "path": {
                        "pathfinding": False,
                        "convert_sonic_drops": True,
                    }
                }
            }
        ).pathfinding(default_pathfinding=True)

        self.assertFalse(path_settings.pathfinding)
        self.assertFalse(path_settings.convert_sonic_drops)
        self.assertFalse(PathSettings(False, True).convert_sonic_drops)

    def test_invalid_pathfinding_setting_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings.from_values(
                {"service": {"path": {"pathfinding": "default"}}}
            ).pathfinding(default_pathfinding=True)


if __name__ == "__main__":
    unittest.main()
