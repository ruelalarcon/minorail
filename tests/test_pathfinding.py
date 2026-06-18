import unittest

from runner.pathfinding import PathfindingOptions, pathfinding_options


class PathfindingOptionsTests(unittest.TestCase):
    def test_default_setting_uses_consumer_default(self) -> None:
        settings = {"service": {"path": {"pathfinding": "default"}}}

        self.assertTrue(
            pathfinding_options(settings, default_pathfinding=True).pathfinding
        )
        self.assertFalse(
            pathfinding_options(settings, default_pathfinding=False).pathfinding
        )

    def test_settings_value_overrides_consumer_default(self) -> None:
        self.assertTrue(
            pathfinding_options(
                {"service": {"path": {"pathfinding": True}}},
                default_pathfinding=False,
            ).pathfinding
        )
        self.assertFalse(
            pathfinding_options(
                {"service": {"path": {"pathfinding": False}}},
                default_pathfinding=True,
            ).pathfinding
        )

    def test_cli_override_wins_over_settings(self) -> None:
        settings = {"service": {"path": {"pathfinding": False}}}

        self.assertTrue(
            pathfinding_options(
                settings,
                default_pathfinding=False,
                pathfinding=True,
            ).pathfinding
        )

    def test_conversion_is_inert_without_path_output(self) -> None:
        options = pathfinding_options(
            {
                "service": {
                    "path": {
                        "pathfinding": False,
                        "convert_sonic_drops": True,
                    }
                }
            },
            default_pathfinding=True,
        )

        self.assertFalse(options.pathfinding)
        self.assertFalse(options.convert_sonic_drops)
        self.assertFalse(PathfindingOptions(False, True).convert_sonic_drops)

    def test_invalid_pathfinding_setting_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            pathfinding_options(
                {"service": {"path": {"pathfinding": "auto"}}},
                default_pathfinding=True,
            )


if __name__ == "__main__":
    unittest.main()
