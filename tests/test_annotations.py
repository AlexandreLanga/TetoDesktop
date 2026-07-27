from pathlib import Path
import unittest

from roof_analyzer.annotations import issue_matches_image, normalize_coordinates


class NormalizeCoordinatesTests(unittest.TestCase):
    def test_converts_normalized_coordinates_to_pixels(self) -> None:
        coordinates = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}

        self.assertEqual(normalize_coordinates(coordinates, 1000, 500), (100, 100, 300, 200))

    def test_keeps_absolute_coordinates(self) -> None:
        coordinates = {"x": 50, "y": 20, "width": 100, "height": 80}

        self.assertEqual(normalize_coordinates(coordinates, 1000, 500), (50, 20, 100, 80))

    def test_rejects_negative_dimensions(self) -> None:
        self.assertIsNone(normalize_coordinates({"width": -1, "height": 1}, 100, 100))


class IssueMatchesImageTests(unittest.TestCase):
    def test_matches_image_by_file_name(self) -> None:
        issue = {"image_name": "FOTO.JPG"}

        self.assertTrue(issue_matches_image(issue, 0, Path("imagens/foto.jpg")))

    def test_matches_image_by_zero_based_index(self) -> None:
        self.assertTrue(issue_matches_image({"image_index": "1"}, 1, Path("foto.jpg")))

    def test_does_not_match_an_invalid_index(self) -> None:
        self.assertFalse(issue_matches_image({"image_index": "abc"}, 0, Path("foto.jpg")))
