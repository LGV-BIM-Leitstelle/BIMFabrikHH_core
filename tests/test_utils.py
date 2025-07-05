"""
Unit tests for utility functions.
"""

import pytest
from BIMFabrikHH.utils.math_operations import MathTool


class TestMathTool:
    """Test cases for MathTool utility class."""

    def test_float_4f_positive_number(self):
        """Test formatting positive float to 4 decimal places."""
        result = MathTool.float_4f("123.456789")
        assert result == "123.4568"

    def test_float_4f_negative_number(self):
        """Test formatting negative float to 4 decimal places."""
        result = MathTool.float_4f("-123.456789")
        assert result == "-123.4568"

    def test_float_4f_zero(self):
        """Test formatting zero to 4 decimal places."""
        result = MathTool.float_4f("0")
        assert result == "0.0000"

    def test_float_4f_small_number(self):
        """Test formatting small number to 4 decimal places."""
        result = MathTool.float_4f("0.000123")
        assert result == "0.0001"

    def test_float_4f_large_number(self):
        """Test formatting large number to 4 decimal places."""
        result = MathTool.float_4f("1234567.89")
        assert result == "1234567.8900"

    def test_float_4f_integer_string(self):
        """Test formatting integer string to 4 decimal places."""
        result = MathTool.float_4f("42")
        assert result == "42.0000"

    def test_float_4f_scientific_notation(self):
        """Test formatting scientific notation to 4 decimal places."""
        result = MathTool.float_4f("1.23e-4")
        assert result == "0.0001"

    def test_float_2f_positive_number(self):
        """Test formatting positive float to 2 decimal places."""
        result = MathTool.float_2f("123.456789")
        assert result == "123.46"

    def test_float_2f_negative_number(self):
        """Test formatting negative float to 2 decimal places."""
        result = MathTool.float_2f("-123.456789")
        assert result == "-123.46"

    def test_float_2f_zero(self):
        """Test formatting zero to 2 decimal places."""
        result = MathTool.float_2f("0")
        assert result == "0.00"

    def test_float_2f_small_number(self):
        """Test formatting small number to 2 decimal places."""
        result = MathTool.float_2f("0.00123")
        assert result == "0.00"

    def test_float_2f_large_number(self):
        """Test formatting large number to 2 decimal places."""
        result = MathTool.float_2f("1234567.89")
        assert result == "1234567.89"

    def test_float_2f_integer_string(self):
        """Test formatting integer string to 2 decimal places."""
        result = MathTool.float_2f("42")
        assert result == "42.00"

    def test_float_2f_scientific_notation(self):
        """Test formatting scientific notation to 2 decimal places."""
        result = MathTool.float_2f("1.23e-4")
        assert result == "0.00"

    def test_float_4f_invalid_input_raises_value_error(self):
        """Test that invalid input raises ValueError for float_4f."""
        with pytest.raises(ValueError):
            MathTool.float_4f("not_a_number")

    def test_float_2f_invalid_input_raises_value_error(self):
        """Test that invalid input raises ValueError for float_2f."""
        with pytest.raises(ValueError):
            MathTool.float_2f("not_a_number")

    def test_float_4f_empty_string_raises_value_error(self):
        """Test that empty string raises ValueError for float_4f."""
        with pytest.raises(ValueError):
            MathTool.float_4f("")

    def test_float_2f_empty_string_raises_value_error(self):
        """Test that empty string raises ValueError for float_2f."""
        with pytest.raises(ValueError):
            MathTool.float_2f("")

    def test_float_4f_none_raises_type_error(self):
        """Test that None raises TypeError for float_4f."""
        with pytest.raises(TypeError):
            MathTool.float_4f(None)  # type: ignore

    def test_float_2f_none_raises_type_error(self):
        """Test that None raises TypeError for float_2f."""
        with pytest.raises(TypeError):
            MathTool.float_2f(None)  # type: ignore

    def test_float_4f_rounding_up(self):
        """Test rounding up behavior for float_4f."""
        result = MathTool.float_4f("123.4565")
        assert result == "123.4565"

    def test_float_4f_rounding_down(self):
        """Test rounding down behavior for float_4f."""
        result = MathTool.float_4f("123.4564")
        assert result == "123.4564"

    def test_float_2f_rounding_up(self):
        """Test rounding up behavior for float_2f."""
        result = MathTool.float_2f("123.455")
        assert result == "123.45"

    def test_float_2f_rounding_down(self):
        """Test rounding down behavior for float_2f."""
        result = MathTool.float_2f("123.454")
        assert result == "123.45"
