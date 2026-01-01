"""
Unit tests for utility functions.
"""

import pytest

from BIMFabrikHH_core.core.utils import MathTool


class TestMathTool:
    """Test cases for MathTool utility class."""

    def test_float_4f_basic_functionality(self):
        """Test basic functionality of float_4f method."""
        # Test positive number
        assert MathTool.float_4f("123.456789") == "123.4568"
        # Test negative number
        assert MathTool.float_4f("-123.456789") == "-123.4568"
        # Test zero
        assert MathTool.float_4f("0") == "0.0000"
        # Test integer string
        assert MathTool.float_4f("42") == "42.0000"

    def test_float_2f_basic_functionality(self):
        """Test basic functionality of float_2f method."""
        # Test positive number
        assert MathTool.float_2f("123.456789") == "123.46"
        # Test negative number
        assert MathTool.float_2f("-123.456789") == "-123.46"
        # Test zero
        assert MathTool.float_2f("0") == "0.00"
        # Test integer string
        assert MathTool.float_2f("42") == "42.00"

    def test_float_4f_edge_cases(self):
        """Test edge cases for float_4f method."""
        # Test scientific notation
        assert MathTool.float_4f("1.23e-4") == "0.0001"
        # Test large number
        assert MathTool.float_4f("1234567.89") == "1234567.8900"
        # Test small number
        assert MathTool.float_4f("0.000123") == "0.0001"

    def test_float_2f_edge_cases(self):
        """Test edge cases for float_2f method."""
        # Test scientific notation
        assert MathTool.float_2f("1.23e-4") == "0.00"
        # Test large number
        assert MathTool.float_2f("1234567.89") == "1234567.89"
        # Test small number
        assert MathTool.float_2f("0.00123") == "0.00"

    def test_float_4f_error_handling(self):
        """Test error handling for float_4f method."""
        # Test invalid input
        with pytest.raises(ValueError):
            MathTool.float_4f("not_a_number")
        # Test empty string
        with pytest.raises(ValueError):
            MathTool.float_4f("")
        # Test None
        with pytest.raises(TypeError):
            MathTool.float_4f(None)  # type: ignore

    def test_float_2f_error_handling(self):
        """Test error handling for float_2f method."""
        # Test invalid input
        with pytest.raises(ValueError):
            MathTool.float_2f("not_a_number")
        # Test empty string
        with pytest.raises(ValueError):
            MathTool.float_2f("")
        # Test None
        with pytest.raises(TypeError):
            MathTool.float_2f(None)  # type: ignore
