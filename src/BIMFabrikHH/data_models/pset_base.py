from typing import Generic, Literal, TypeVar, ClassVar, get_args
import pint

from pydantic import BaseModel
from pydantic_core import core_schema

U = pint.UnitRegistry()

class PropertySetTemplate(BaseModel):
    pset_name: ClassVar[str]

class Quantity(Generic[TypeVar("")]):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, _):
        prescribed = U.get_dimensionality(get_args(get_args(source_type)[0])[0])

        def _validate(val):
            if not isinstance(val, pint.Quantity):
                try:
                    val = U.Quantity(*val) if isinstance(val, (list, tuple)) else U.Quantity(val)
                except Exception as e:
                    raise ValueError(f"Could not parse quantity {val!r}") from e

            if not val.check(prescribed):
                raise ValueError(f"{val!r} does not have dimension {prescribed!r}")

            return val#.to_base_units()

        return core_schema.no_info_after_validator_function(
            _validate,
            core_schema.any_schema(),
        )

Length = Literal["[length]"]
Time = Literal["[time]"]
