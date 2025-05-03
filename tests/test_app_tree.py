import unittest
from io import BytesIO
from unittest.mock import patch

import pandas as pd
from src.BIMFabrikHH.apps.baum.app import BaumModeller
from src.BIMFabrikHH.apps.baum.baum_col_names import DfColTree
from src.BIMFabrikHH.pydantic_models.params_bbox import BoundingBoxParams


class TestBaumModeller(unittest.TestCase):
    @patch("src.BIMFabrikHH.core.request_oaf.HamburgOGCAPI.fetch_data")
    def test_get_oaf_tree_df(self, mock_fetch_data):
        # Mocking the response from fetch_data
        mock_fetch_data.return_value = {
            "features": [
                {
                    "properties": {
                        "gid": 1,
                        "baumid": 101,
                        "baumnummer": "A123",
                        "gattung_deutsch": "Oak",
                        "art_deutsch": "Quercus robur",
                        "sorte_deutsch": "Common oak",
                        "pflanzjahr": 2000,
                        "kronendurchmesser": 12.5,
                        "stammumfang": 250,
                        "strasse": "Main Street",
                        "stadtteil": "City Center",
                        "bezirk": "District 1",
                    }
                }
            ]
        }

        # Create an instance of BaumModeller
        baum_modeller = BaumModeller()

        # Define bounding box coordinates
        x1, y1, x2, y2 = 9.9, 53.5, 10.0, 53.6
        df = baum_modeller.get_oaf_tree_df(x1, y1, x2, y2)

        # Check if the dataframe is not empty and has the correct structure
        self.assertFalse(df.empty)
        self.assertIn(DfColTree.STAMMUMFANG_BK, df.columns)
        self.assertEqual(df.shape[0], 1)  # Only one row in mock data

    def test_convert_umfang_durchmesser(self):
        # Test data
        df = pd.DataFrame({DfColTree.STAMMUMFANG_BK: [250, 500, 40]})

        # Create an instance of BaumModeller
        baum_modeller = BaumModeller()

        # Apply the conversion function
        df[DfColTree.STAMMUMFANG_BK] = baum_modeller.convert_umfang_durchmesser(
            df, DfColTree.STAMMUMFANG_BK, lambda x: round(x, 2)
        )

        # Check if the values are correctly converted
        self.assertEqual(df[DfColTree.STAMMUMFANG_BK].iloc[0], 0.8)  # 250/100/pi -> 0.8
        self.assertEqual(df[DfColTree.STAMMUMFANG_BK].iloc[1], 1.59)  # 500/100/pi -> 1.59
        self.assertEqual(df[DfColTree.STAMMUMFANG_BK].iloc[2], 0.13)  # 40/100/pi -> 0.13

    @patch("src.BIMFabrikHH.core.baum_manager.BaumManager.place_trees_from_df")
    @patch("src.BIMFabrikHH.core.ifc_utils.IfcFileCreator.save_ifc_in_memory")
    def test_create_tree_model(self, mock_save_ifc, mock_place_trees):
        # Mock the tree data frame and the IFC saving functionality
        mock_save_ifc.return_value = BytesIO(b"dummy_ifc_data")
        mock_place_trees.return_value = None

        # Define mock model params with valid bounding box coordinates
        class MockModelParams:
            def __init__(self):
                # Adjust the bounding box values to pass validation
                self.bbox = BoundingBoxParams(min_x=10.0, min_y=53.4, max_x=10.3, max_y=53.5)
                self.project_name = "Test Project"
                self.level_of_geom = 2

        model_params = MockModelParams()

        # Create an instance of BaumModeller
        baum_modeller = BaumModeller()

        # Call the method to create tree model
        result = baum_modeller.create_tree_model(model_params)

        # Assert the result is not None
        self.assertIsNotNone(result, "The IFC model should not be None.")

        # Assert that the result is a BytesIO object and check its contents
        self.assertIsInstance(result, BytesIO)
        self.assertEqual(result.getvalue(), b"dummy_ifc_data")

    @patch("src.BIMFabrikHH.core.request_oaf.HamburgOGCAPI.fetch_data")
    def test_get_oaf_tree_df_no_data(self, mock_fetch_data):
        # Mocking the response from fetch_data to simulate no data
        mock_fetch_data.return_value = {"features": []}

        # Create an instance of BaumModeller
        baum_modeller = BaumModeller()

        # Define bounding box coordinates
        x1, y1, x2, y2 = 9.9, 53.5, 10.0, 53.6
        df = baum_modeller.get_oaf_tree_df(x1, y1, x2, y2)

        # Check that the dataframe is empty
        self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()
