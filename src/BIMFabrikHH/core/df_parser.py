from dataclasses import dataclass
from typing import Dict, Any, List

import pandas as pd

from BIMFabrikHH.core.profile_stadtmobiliar import profiles_stadtmobiliar
from BIMFabrikHH.default.paths import PathConfig


# from src.BIMFabrikHH_intern.default.paths import PathConfig

# from BIMFabrikHH.apps.stadtmobiliar.profile_stadtmobiliar import profiles_stadtmobiliar
# from BIMFabrikHH.default.paths import PathConfig

# from src.BIMFabrikHH_intern.stadtmobiliar.profile_stadtmobiliar import profiles_stadtmobiliar


@dataclass
class DfCol:
    """Dataclass representing the column names used in the dataframes."""

    REM2: str = "REM2"
    BAUM_INFO_ORIG: str = "BAUMINFO-STAMM_Datenquelle"
    BAUM_NR: str = "_Baumnummer"
    REM1: str = "REM1"
    EASTING: str = "Easting"
    EASTING_UTM = "Easting_UTM"
    ELEVATION: str = "Elevation"
    GATTUNG: str = "_Gattung"
    KRONENDURCHMESSER: str = "_Kronendurchmesser"
    LINE_SEPARATOR = "*" * 150
    NORTHING: str = "Northing"
    POS_X: str = "Position X"
    POS_Y: str = "Position Y"
    STAMMBASIS: str = "_Stammbasis"
    STAMMUMFANG: str = "_Stammumfang"
    STAMMUMFANG_BK: str = "stammumfang"
    REFERENCE_LINE: str = "Referenzlinie"
    TYP: str = "Typ"
    OBJEKT_NR: str = "Objektnummer"
    OBJEKTCODIERUNG: str = "OBJEKTCODIERUNG"
    FARBE = "Farbe"

    LAENGE = "Laenge"
    TIEFE = "Tiefe"
    HOEHE = "Hoehe"
    METHODE = "Methode"


class DfParser:
    """Parser for handling and transforming data from text input to a pandas DataFrame."""

    def __init__(self): ...

    @staticmethod
    def create_df_from_txt(combined_content: str) -> pd.DataFrame:
        """Creates a DataFrame from the given text content.

        Args:
            combined_content (str): The combined text content containing data to be parsed.

        Returns:
            pd.DataFrame: The resulting DataFrame created from the text content.
        """

        column_names = [
            DfCol.EASTING,
            DfCol.NORTHING,
            DfCol.ELEVATION,
            DfCol.REM1,
            DfCol.REM2,
            DfCol.FARBE,
        ]

        data_dict = {}

        for line in combined_content.split("\n"):
            # print(line)

            # Split each line into columns using spaces as separators
            parts = line.strip().split()
            # report.append(line)
            if parts:
                key = parts[0]
                values = parts[1:]

                # Create a dictionary with column names and values
                try:
                    row_data = {column_names[i]: value for i, value in enumerate(values)}
                    # Add the key-value pair to the main dictionary
                    data_dict[key] = row_data
                except Exception as e:
                    print(e)
                    data_dict = {}

        # pprint(data_dict, width=200)
        df_combined = pd.DataFrame(data_dict).T
        # Reset index and convert to integer type
        df_combined.reset_index(inplace=True)

        # Ensure 'index' column is integer type
        df_combined["index"] = df_combined["index"].astype(int)

        # Sort by the 'index' column
        df_combined.sort_values(by="index", inplace=True)

        # Optionally, reset index to clean up
        # df_combined.reset_index(drop=True, inplace=True)

        return df_combined

    @staticmethod
    def create_df_from_excel(excel_file_path) -> pd.DataFrame:
        df = pd.read_excel(excel_file_path)
        return df

    @staticmethod
    def create_df_from_csv(csv_file_path):

        columns_to_keep = [
            "Name",
            "Layer",
            "Position X",
            "Position Y",
            "Position Z",
            "Drehung",
        ]

        # Read CSV headers first to check available columns
        df_preview = pd.read_csv(csv_file_path, delimiter=";", nrows=0)

        # Add "Drehung.1" only if it exists in the file
        required_columns = ["Effektiver Typ","Drehung.1", "NUMMER", "Nummer", "Handle"]
        columns_to_keep.extend([col for col in required_columns if col in df_preview.columns])

        df = pd.read_csv(csv_file_path, delimiter=";", usecols=columns_to_keep)

        # if "Drehung.1" in df.columns:
        #     df = df.drop(columns=["Drehung"], errors="ignore")  # Remove "Drehung" if it exists
        #     df = df.rename(columns={"Drehung.1": "Drehung"})  # Rename "Drehung.1" to "Drehung"

        df = df.rename(
            columns={
                "Name": "Blockname",
                "Position X": "Easting",
                "Position Y": "Northing",
                "Position Z": "Elevation",
            }
        )

        # convert gradians to degree

        # df["Drehung"] = (
        #     df["Drehung"]
        #     .str.replace("g", "", regex=False)  # Remove 'g'
        #     .apply(lambda x: float(x) * 0.9 if x.replace(".", "", 1).isdigit() else None)
        # )
        
        # funktioniert nicht mehr
        """
        df["Drehung"] = (
            df["Drehung"]
            .astype(str)  # Convert everything to string first
            .str.replace("g", "", regex=False)  # Remove 'g'
            .apply(lambda x: float(x) * 0.9 if x.replace(".", "", 1).isdigit() else None)
        )
        """

        df["Einfuegepunkt"] = 1

        df_profiles_stadtmobiliar = pd.read_excel(PathConfig.PROFILES_STADTMOBILIAR, dtype={"ID": str})
        df_profiles_stadtmobiliar = df_profiles_stadtmobiliar.drop(columns=["Einfuegepunkt"])

        # Merge df1 with df2 on the "ID" column (only keeping matches)
        df_merged = df.merge(df_profiles_stadtmobiliar, on="Blockname", how="left")  # Use "inner" to keep only matches

        # df_merged["Original_Index"] = df.index.astype(int)
        # df_merged = df_merged.sort_values(by="Original_Index")
        # df_merged = df_merged.reset_index()

        # Remove rows where 'Name' column is None or NaN
        df_cleaned = df_merged.dropna(subset=["Typ"])
        # df_cleaned["Midpoint"] = None
        # df_cleaned.loc[:, "Midpoint"] = None
        df_cleaned = df_cleaned.assign(Midpoint=None)

        # print(df_cleaned)

        # print(df.head(50))

        return df_cleaned

    @staticmethod
    def process_referenzpunkt(idx, df, einfuegepunkt, rows_to_delete):
        """Helper function to set Referenzpunkte based on Einfuegepunkt value."""
        row = df.iloc[idx]
        df.at[idx, "Referenzpunkt_1"] = f"{row[DfCol.EASTING]},{row[DfCol.NORTHING]}"

        if einfuegepunkt == 2:
            next_row_idx = idx + 1
            if next_row_idx < len(df):
                next_row = df.iloc[next_row_idx]
                df.at[idx, "Referenzpunkt_2"] = f"{next_row[DfCol.EASTING]}, {next_row[DfCol.NORTHING]}"
                if row["REFERENZLINIE"] != next_row["REFERENZLINIE"]:
                    rows_to_delete.add(next_row_idx)

        elif einfuegepunkt == 3:
            next_row_idx = idx + 1
            if next_row_idx < len(df):
                next_row = df.iloc[next_row_idx]
                df.at[idx, "Referenzpunkt_2"] = f"{next_row[DfCol.EASTING]}, {next_row[DfCol.NORTHING]}"
                rows_to_delete.add(next_row_idx)

            third_row_idx = idx + 2
            if third_row_idx < len(df):
                third_row = df.iloc[third_row_idx]
                df.at[idx, "Referenzpunkt_3"] = f"{third_row[DfCol.EASTING]},{third_row[DfCol.NORTHING]}"
                rows_to_delete.add(third_row_idx)

    @staticmethod
    def process_dataframe(df: pd.DataFrame, profiles: Dict[str, List[Any]]) -> Dict[str, Dict[str, Any]]:
        """Processes the DataFrame and merges it with the profiles.

        Args:
            df (pd.DataFrame): The DataFrame containing the data.
            profiles (Dict[str, List[Any]]): The mapping of profile data.

        Returns:
            Dict[str, Dict[str, Any]]: A merged dictionary containing the processed data.
        """
        # Initialize an empty dictionary to hold the merged data
        merged_dict = {}

        # Iterate through the profiles to filter and merge
        for key, value in profiles.items():
            # Filter the DataFrame based on the desired ending in the REM1 column
            filtered_df = df[df[DfCol.REM1].str.endswith(key)]

            # Process each row in the filtered DataFrame
            for _, row in filtered_df.iterrows():
                # Create a new entry in the merged dictionary
                merged_entry = row.to_dict()
                # Add the profile details
                merged_entry["Typ"] = ""
                merged_entry["Blockname"] = ""
                merged_entry["Layer"] = ""
                merged_entry["Methode"] = ""
                merged_entry["Laenge"] = ""
                merged_entry["Tiefe"] = ""
                merged_entry["Hoehe"] = ""
                merged_entry["Einfuegepunkt"] = ""
                merged_entry["Farbe"] = ""

                # Add the entry to the merged dictionary using the index as the key
                merged_dict[row.name] = merged_entry  # Use the row index as the key

        return merged_dict

    @staticmethod
    def assign_referenzpunkte_3_p(sub_df):
        # If the group has exactly 3 rows
        if len(sub_df) == 3:
            # Assign the Referenzpunkte based on the first three rows
            sub_df["Referenzpunkt_1"] = f'{sub_df.iloc[0]["Easting"]},{sub_df.iloc[0]["Northing"]}'
            sub_df["Referenzpunkt_2"] = f'{sub_df.iloc[1]["Easting"]},{sub_df.iloc[1]["Northing"]}'
            sub_df["Referenzpunkt_3"] = f'{sub_df.iloc[2]["Easting"]},{sub_df.iloc[2]["Northing"]}'

            # Keep only the first row and discard the second and third rows
            sub_df = sub_df.iloc[[0]]

        # If the group has more than 3 rows (this should not happen if grouping is done correctly)
        elif len(sub_df) > 3:
            # Assign the first 3 Referenzpunkte based on the first three rows
            sub_df["Referenzpunkt_1"] = f'{sub_df.iloc[0]["Easting"]},{sub_df.iloc[0]["Northing"]}'
            sub_df["Referenzpunkt_2"] = f'{sub_df.iloc[1]["Easting"]},{sub_df.iloc[1]["Northing"]}'
            sub_df["Referenzpunkt_3"] = f'{sub_df.iloc[2]["Easting"]},{sub_df.iloc[2]["Northing"]}'

            # Keep only the first row
            sub_df = sub_df.iloc[[0]]

        return sub_df

    @staticmethod
    def assign_referenzpunkte_2_p(sub_df):
        # if isinstance(sub_df, pd.Series):  # Check if sub_df is a single row
        #     # Handle as a row if necessary
        #     return sub_df
        # If the group has exactly 2 rows, drop the second one

        if len(sub_df) > 1 and sub_df["Einfuegepunkt"].iloc[0] == 2:

            # sub_df["Referenzpunkt_1"] = sub_df.iloc[0]["Easting"]
            # sub_df["Referenzpunkt_2"] = sub_df.iloc[1][f'{["Easting"]},{["Northing"]}']
            # pass
            sub_df["Referenzpunkt_1"] = f'{sub_df.iloc[0]["Easting"]},{sub_df.iloc[0]["Northing"]}'
            sub_df["Referenzpunkt_2"] = f'{sub_df.iloc[1]["Easting"]},{sub_df.iloc[1]["Northing"]}'

        if len(sub_df) == 2:
            # Keep only the first row
            sub_df = sub_df.iloc[[0]]

        return sub_df

    def decodierung_tabelle(self, combined_text: str) -> pd.DataFrame:

        df = self.parse_data_from_txt(combined_text)
        df["Original_Index"] = df.index.astype(int)
        df = df.sort_values(by="Original_Index")
        df = df.reset_index()

        df["Group"] = 0.0

        df["Einfuegepunkt"] = pd.to_numeric(df["Einfuegepunkt"], errors="coerce").fillna(0).astype(int)
        df["Referenzpunkt_1"] = "0.0"
        df["Referenzpunkt_2"] = "0.0"
        df["Referenzpunkt_3"] = "0.0"

        df[DfCol.EASTING] = df[DfCol.EASTING].astype(float)
        df[DfCol.NORTHING] = df[DfCol.NORTHING].astype(float)
        df[DfCol.ELEVATION] = df[DfCol.ELEVATION].astype(float)

        df[DfCol.REM1] = df[DfCol.REM1].astype(str)
        df["PUNKTOPTION"] = (df[DfCol.REM1].str[0]).astype(int)
        df["OPTION_REM1"] = df[DfCol.REM1].str[1].astype(int)
        df["PLATZHALTER"] = df[DfCol.REM1].str[2].astype(int)
        df["PROFILCODIERUNG"] = df[DfCol.REM1].str[3].astype(int)
        df["REFERENZLINIE"] = df[DfCol.REM1].str[4].astype(int)
        df[DfCol.OBJEKTCODIERUNG] = df[DfCol.REM1].str[5:8]
        df["OPTION_REM2"] = df[DfCol.REM2].str[0:2].astype(int)
        df["INFO_REM2"] = df[DfCol.REM2].str[2:8].astype(int)
        # mapping_dict = {"8": "Punkte mit Hoehe", "9": "Punkte ohne Hoehe"}
        # df["PUNKTOPTION"] = df["PUNKTOPTION"].map(mapping_dict)

        df.loc[
            df["Einfuegepunkt"] == 1,
            ["Referenzpunkt_1", "Referenzpunkt_2", "Referenzpunkt_3"],
        ] = 0.0

        # Step 4: Initialize a list to keep track of row indices to delete
        rows_to_delete = set()  # To store rows that need to be deleted

        # Iterate through DataFrame using iterrows
        for idx, row in df.iterrows():
            # Check if the 'Einfuegepunkt' is 1 and assign Referenzpunkt_1
            if row["Einfuegepunkt"] == 1:
                df.at[idx, "Referenzpunkt_1"] = f'{row["Easting"]},{row["Northing"]}'
                # pass

            # Check if the 'Einfuegepunkt' is 3
            elif row["Einfuegepunkt"] == 3:
                next_row_idx = int(idx) + 1
                third_row_idx = int(idx) + 2
                df.at[idx, "Referenzpunkt_1"] = f'{row["Easting"]},{row["Northing"]}'

                # Ensure we do not go out of bounds when accessing the next and third rows
                if next_row_idx < len(df):
                    next_row = df.iloc[next_row_idx]
                    third_row = df.iloc[third_row_idx]

                    # Assign Referenzpunkte based on next and third rows
                    df.at[idx, "Referenzpunkt_2"] = f'{next_row["Easting"]},{next_row["Northing"]}'
                    df.at[idx, "Referenzpunkt_3"] = f'{third_row["Easting"]},{third_row["Northing"]}'

                    rows_to_delete.add(next_row_idx)
                    rows_to_delete.add(third_row_idx)

        # Step 6: Remove rows marked for deletion
        # rows_to_delete = sorted(rows_to_delete, reverse=True)
        df = df.drop(rows_to_delete).reset_index(drop=True)

        # # Reset the index after dropping rows to maintain a clean index sequence
        # df.reset_index(drop=True, inplace=True)
        df = df.reset_index()
        group_number = 0
        group_map = []

        for i in range(len(df)):
            if df.loc[i, "Einfuegepunkt"] == 2:
                if i == 0 or df.loc[i, "REFERENZLINIE"] != df.loc[i - 1, "REFERENZLINIE"]:
                    group_number += 1
                group_map.append(group_number)
            else:
                group_map.append(None)

        df["Group"] = group_map

        # Apply the function to groups instead of individual elements if needed
        # df = df.groupby("Group", dropna=False).apply(self.assign_referenzpunkte_2_p)
        df = df.groupby("Group", dropna=False).apply(self.assign_referenzpunkte_2_p, include_groups=False).reset_index()

        df.dropna(subset=["Typ"], inplace=True)

        df.reset_index(drop=True, inplace=True)
        # df.drop(columns="Group", inplace=True)

        """
        calculate midpoint
        """
        # Filter rows where Einfuegepunkt == 2 and there's only one row per Group
        filtered_df = df[df["Einfuegepunkt"] == 2]
        unique_groups = filtered_df.groupby("Group").filter(lambda g: len(g) == 1)

        # Add a new column for the midpoint
        df.loc[unique_groups.index, "Midpoint"] = unique_groups.apply(
            lambda row: DfParser.calculate_midpoint(row["Referenzpunkt_1"], row["Referenzpunkt_2"]),
            axis=1,
        )
        df.loc[df["Midpoint"].notna(), "Referenzpunkt_1"] = df["Midpoint"]

        return df

    def parse_data_from_txt(self, combined_content: str) -> pd.DataFrame:
        """Parses the given text content and merges with additional profile data.

        Args:
            combined_content (str): The combined text content containing data to be parsed.

        Returns:
            pd.DataFrame: The resulting DataFrame after merging with additional profile data.
        """
        column_names = [
            DfCol.EASTING,
            DfCol.NORTHING,
            DfCol.ELEVATION,
            DfCol.REM1,
            DfCol.REM2,
            DfCol.FARBE,
        ]

        data_dict = {}
        # data_filtered = {}

        for line in combined_content.split("\n"):
            # print(line)

            # Split each line into columns using spaces as separators
            parts = line.strip().split()
            # report.append(line)
            if parts:
                key = parts[0]
                values = parts[1:]

                # Create a dictionary with column names and values
                row_data = {column_names[i]: value for i, value in enumerate(values)}

                # Add the key-value pair to the main dictionary
                data_dict[key] = row_data

        # pprint(data_dict, width=200, sort_dicts=False)

        # pprint(profiles_stadtmobiliar, width=200, sort_dicts=False)

        merged_dict = {}
        for key, value in profiles_stadtmobiliar.items():
            data_filtered: dict = self.filter_data_by_ending(data_dict, key)
            # print("*" * 100)
            # pprint(data_filtered, width=200, sort_dicts=False)

            for k, v in data_filtered.items():
                v["Typ"] = value[0]
                v["Blockname"] = value[1]
                v["Layer"] = value[2]
                v["Methode"] = value[3]
                v["Laenge"] = value[4]
                v["Tiefe"] = value[5]
                v["Hoehe"] = value[6]
                v["Einfuegepunkt"] = value[7]
                v["Farbe"] = value[8]

                merged_dict[k] = v

        merged_dict.update(data_dict)
        # pprint(merged_dict, width=100, sort_dicts=True)

        """        
        merged_dict = {}
        for key, value in profiles_stadtmobiliar.items():
            data_filtered: dict = self.filter_data_by_ending(data_dict, key)
            for k, v in data_filtered.items():
                v["Typ"] = value[0]
                v["Blockname"] = value[1]
                v["Layer"] = value[2]
                v["Methode"] = value[3]
                v["Laenge"] = value[4]
                v["Tiefe"] = value[5]
                v["Hoehe"] = value[6]
                v["Einfuegepunkt"] = value[7]
                v["Farbe"] = value[8]

                merged_dict[k] = v
        """
        # df = pd.DataFrame(data_dict).T
        df = pd.DataFrame(merged_dict).T
        self.aggregate_df(df)

        return df

    @staticmethod
    def filter_data_by_ending(data_dict: Dict[str, Dict[str, Any]], desired_type: str) -> Dict[str, Dict[str, Any]]:
        """Filters the data dictionary by matching the ending of REM1 column values.

        Args:
            data_dict (Dict[str, Dict[str, Any]]): The dictionary containing the data.
            desired_type (str): The desired REM1 value ending to filter by.

        Returns:
            Dict[str, Dict[str, Any]]: The filtered dictionary containing only the data with the desired ending.
        """

        filtered_data = {}
        for key, values in data_dict.items():
            # re.search('379$', txt)
            # if values[DfCol.REM1] == desired_type:
            if values[DfCol.REM1].endswith(desired_type):
                # if values[DfCol.REM1] == desired_type:
                filtered_data[key] = values
                # print(key, values)
            # else:
            #     print(key, values)

        # pprint(filtered_data, width=200, sort_dicts=False)
        return filtered_data

    @staticmethod
    def filter_data_by_type(data_dict: Dict[str, Dict[str, Any]], desired_type: str) -> Dict[str, Dict[str, Any]]:
        """Filters the data dictionary by a specific REM1 value.

        Args:
            data_dict (Dict[str, Dict[str, Any]]): The dictionary containing the data.
            desired_type (str): The desired REM1 value to filter by.

        Returns:
            Dict[str, Dict[str, Any]]: The filtered dictionary containing only the data with the desired REM1 value.
        """

        filtered_data = {}
        for key, values in data_dict.items():
            if values[DfCol.REM1] == desired_type:
                filtered_data[key] = values

        return filtered_data

    @classmethod
    def aggregate_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates the DataFrame based on the 'Typ' column.

        Args:
            df (pd.DataFrame): The DataFrame to be aggregated.

        Returns:
            pd.DataFrame: The aggregated DataFrame.
        """
        df_groups = None
        try:
            df_groups = (
                df.groupby(DfCol.TYP)
                .agg(
                    Anzahl=(DfCol.TYP, "size"),
                    **{
                        col: (col, "first")
                        for col in [
                            "Teilmodell",
                            "IDEbene1",
                            "IDEbene2",
                            "IDEbene3",
                            DfCol.LAENGE,
                            DfCol.HOEHE,
                            DfCol.TIEFE,
                            DfCol.METHODE,
                            DfCol.FARBE,
                        ]
                    },
                )
                .reset_index()
            )
        except KeyError as e:
            print(e)

        return df_groups

    @staticmethod
    def get_column_value(df, condition_col, condition_val, target_col, default="None"):
        """
        Retrieve the first match for a target column based on a condition, or return a default value.

        Parameters:
            df (pd.DataFrame): The DataFrame to search.
            condition_col (str): The column name to apply the condition on.
            condition_val: The value to match in the condition column.
            target_col (str): The column name to retrieve the value from.
            default (str): The default value to return if no match is found.

        Returns:
            str: The matched value or the default value.
        """
        match = df.loc[df[condition_col] == condition_val, target_col]
        if not match.empty:
            return match.iloc[0]
        # print(f"No match found for {condition_col} = {condition_val} in {target_col}")
        return default

    @staticmethod
    def parse_point(point):
        x, y = map(float, point.split(","))
        return x, y

    @staticmethod
    def calculate_midpoint(point1, point2):
        x1, y1 = DfParser.parse_point(point1)
        x2, y2 = DfParser.parse_point(point2)
        return f"{(x1 + x2) / 2:.4f},{(y1 + y2) / 2:.4f}"

    @staticmethod
    def apply_laterne_typ(df):
        value_dict = {
                "a": {"Typ": "Typ_a", "Hoehe": 9.5},
                "b": {"Typ": "Typ_b", "Hoehe": 8.3},
                "c": {"Typ": "Typ_c", "Hoehe": 3.6},
                "d": {"Typ": "Typ_d", "Hoehe": 9.7},
                "e": {"Typ": "Typ_e", "Hoehe": 4.6},
                "f": {"Typ": "Typ_f", "Hoehe": 7.4},
                "g": {"Typ": "Typ_g", "Hoehe": 5.4},
        }
        try:
            df["Hoehe"] = df.apply(
                    lambda row: value_dict[row["NUMMER"]]["Hoehe"] if row["NUMMER"] in value_dict else row["Hoehe"],
                    axis=1
            )
    
            df["Typ"] = df.apply(
                    lambda row: row["Name"] + "_Typ_" + row["NUMMER"] + "_" + row["Blockname"]
                    if row["NUMMER"] in value_dict
                    else row["Typ"],
                    axis=1
            )
        except Exception as e:
            print(e)

        return df