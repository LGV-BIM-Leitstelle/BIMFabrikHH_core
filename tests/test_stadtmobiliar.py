import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.BIMFabrikHH.apps.stadtmodell.app import process_gml_to_ifc


class TestGMLProcessing(unittest.TestCase):
    def setUp(self):
        """Setup test environment"""
        self.folder_path = r"C:\_Lokale_Daten_ungesichert\__GitHubProjects\BIMFabrik\samples\stadtmodell"
        self.test_files = ["file1.xml", "file2.xml"]

    def test_list_gml_files(self):
        """Test if the script correctly finds GML (.xml) files"""
        with patch("os.listdir", return_value=self.test_files):
            gml_files = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.endswith(".xml")]
            self.assertEqual(len(gml_files), 2)
            self.assertTrue(all(f.endswith(".xml") for f in gml_files))

    @patch("lxml.etree.parse")  # Mock XML parsing first
    @patch("src.apps.stadtmodell.main.process_gml_to_ifc")  # Then mock the main function
    def test_process_gml_to_ifc(self, mock_process_gml_to_ifc, mock_etree_parse):
        """Test if process_gml_to_ifc is called correctly"""

        mock_process_gml_to_ifc.return_value = "Mocked Processed Model"
        mock_etree_parse.return_value = MagicMock()  # Prevents actual XML parsing

        gml_files = [os.path.join(self.folder_path, f) for f in self.test_files]
        folder_path = Path(r"C:\_Lokale_Daten_ungesichert\CityGML_Hamburg\LoD1-DE_HH_2023-04-01")
        result = process_gml_to_ifc(gml_files, "Hamburg Buildings", "Hamburg Site", reset_model=True)

        mock_process_gml_to_ifc.assert_called_once_with(
            gml_files, "Hamburg Buildings", "Hamburg Site", reset_model=True
        )
        self.assertEqual(result, "Mocked Processed Model")


if __name__ == "__main__":
    unittest.main()
