class MathTool:
    """
    A utility class providing methods for formatting floating-point numbers.

    This class contains static methods for formatting a given string representation
    of a float to a specified number of decimal places.

    Methods:

        float_2f(x: str) -> str:
            Format the given string representation of a float to 2 decimal places.

        float_4f(x: str) -> str:
            Format the given string representation of a float to 4 decimal places.

        float_6f(x: str) -> str:
            Format the given string representation of a float to 6 decimal places.
    """

    @staticmethod
    def float_2f(x: str) -> str:
        """
        Format the given string representation of a float to 2 decimal places.

        Args:
            x (str): A string representing a float number.

        Returns:
            str: The formatted float with 2 decimal places.
        """

        x = float(x)
        formatted_float = f"{float(x):.2f}"

        return formatted_float

    @staticmethod
    def float_4f(x: str) -> str:
        """
        Format the given string representation of a float to 4 decimal places.

        Args:
            x (str): A string representing a float number.

        Returns:
            str: The formatted float with 4 decimal places.
        """

        x = float(x)
        formatted_float = f"{float(x):.4f}"

        return formatted_float

    @staticmethod
    def float_6f(x: str) -> str:
        """
        Format the given string representation of a float to 6 decimal places.

        Args:
            x (str): A string representing a float number.

        Returns:
            str: The formatted float with 6 decimal places.
        """

        x = float(x)
        formatted_float = f"{float(x):.6f}"

        return formatted_float
