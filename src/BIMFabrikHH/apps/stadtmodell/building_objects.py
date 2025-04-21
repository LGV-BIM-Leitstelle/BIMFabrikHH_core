from typing import Tuple, List


class Point:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


class Edge:
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end


class Face:
    def __init__(self, points: List[Point]):
        self.points = points


class Building:
    def __init__(self, building_id: str, geometry: Tuple[List[Point], List[List[int]]]):
        self.id = building_id
        self.vertices, self.faces = geometry
        self.address = None
        self.height = None
        self.stories = None
        self.postcode = None
