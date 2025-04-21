from typing import Optional

from pydantic import BaseModel


class IfcProject(BaseModel):
    name: Optional[str] = None
    # longName: Optional[str] = None
    # Phase: Optional[str] = None
    # RepresentationContexts: Optional[List[IfcRepresentationContext]] = None
    # UnitsInContext: Optional[IfcUnitAssignment] = None
    # IsDefinedBy: Optional[List[IfcRelDefinesByProperties]] = None
    # Declares: Optional[List[IfcRelDeclares]] = None
