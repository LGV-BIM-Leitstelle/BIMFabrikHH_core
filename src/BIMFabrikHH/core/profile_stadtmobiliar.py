import pandas as pd

from BIMFabrikHH.default.paths import PathConfig

# from src.BIMFabrikHH_intern.default.paths import PathConfig

PathConfig()
df = pd.read_excel(PathConfig.PROFILES_STADTMOBILIAR, dtype={"ID": str})
profiles_stadtmobiliar = df.set_index("ID").apply(tuple, axis=1).to_dict()
