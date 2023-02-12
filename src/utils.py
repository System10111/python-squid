import math

import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

def calc_boyancy(ship: pm.Body) -> tuple[float, Vec2]:
    # total area under water
    total = 0
    # we also need the center of gravity of the underwater part
    center = Vec2(0, 0)
    for shape in ship.shapes:
        new_verts = []
        for vert in shape.get_vertices():
            vert = ship.local_to_world(vert)
            if vert.y > 0:
                new_verts.append(vert)
            else:
                new_verts.append(Vec2(vert.x, 0))
        new_poly = pm.Poly(None, new_verts)
        area = new_poly.area
        if area > 0:
            total += area
            center += new_poly.center_of_gravity * area

    if total < 1:
        return 0, Vec2(0, 0)

    return total * 1.025, ((center / total) if total > 0 else Vec2(0, 0))
