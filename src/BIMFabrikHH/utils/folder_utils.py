from pathlib import Path


def get_src_dir() -> Path:
    """
    Find the parent directory containing the 'src' folder by traversing up the directory tree.

    Returns:
        Path: The parent directory of the 'src' folder.

    Raises:
        FileNotFoundError: If the 'src' directory is not found within the expected depth.
    """
    path = Path(__file__).resolve()
    max_depth = 10
    for _ in range(max_depth):
        if (path / "src").is_dir():
            # parent of the "src" directory
            return path.parent

        # Move up two levels
        path = path.parent.parent

    raise FileNotFoundError("Could not find 'src' directory within the expected parent directories.")


def check_folder_exists(folder_name: str) -> Path:
    """
    Check if a default_data data folder exists, otherwise use the src directory as base.

    Args:
        folder_name (str): Name of the folder to check or create.

    Returns:
        Path: The resolved path to the folder.
    """
    default_folder = Path(r"C:\Users\Public\Python\AS_BIMFabrik_prototyp\Daten")

    if default_folder.exists():
        folder = default_folder / folder_name
    else:
        src_dir = get_src_dir()
        folder = src_dir / folder_name

    print(f"{folder_name}: {folder}")

    return folder
