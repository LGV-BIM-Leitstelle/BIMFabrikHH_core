"""
Loads and prepares the Stadtmobiliar profile data for use in the BIMFabrikHH core package.
Reads an Excel file containing profile definitions and converts it to a dictionary for fast lookup.
"""

import pandas as pd

from ..default_data.paths import PathConfig

# Ensure PathConfig is initialized
PathConfig()
# Read the Excel file containing profile data
# The 'ID' column is used as the key, and each row is converted to a tuple
# The resulting dictionary maps ID to profile data

df = pd.read_excel(PathConfig.PROFILES_STADTMOBILIAR, dtype={"ID": str})
profiles_stadtmobiliar = df.set_index("ID").apply(tuple, axis=1).to_dict()
