import math

import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

SHIP_HULL_GROUP = 20

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


class Ship():
    def __init__(self, position: Vec2, 
    texture: pr.Texture2D, 
    space: pm.Space, 
    decks: list[tuple[float, float]]
    ):
        self.texture = texture
        self.body = pm.Body()
        self.body.position = position
        hull_size = Vec2(self.texture.width*2, self.texture.height*1.9)
        # body_shape = pm.Poly.create_box(self.body, hull_size, 0)
        body_shape = pm.Poly(self.body, [
            (-hull_size.x/2, hull_size.y/2), 
            (-hull_size.x/2, -hull_size.y*0.5/2),
            (hull_size.x/2, hull_size.y/2),
            (hull_size.x/2, -hull_size.y*0.5/2)
        ])
        body_shape.density = 0.001

        weight_shape = pm.Poly(self.body, [
            (-hull_size.x/5, hull_size.y*2/8), 
            (-hull_size.x/5, hull_size.y*3/8),
            (hull_size.x/5, hull_size.y*3/8),
            (hull_size.x/5, hull_size.y*2/8)
        ])
        weight_shape.density = 0.1

        space.add(self.body, body_shape, weight_shape)
    
    def update(self, dt: float):
        # apply drag
        self.body.velocity *= 1-(1 * dt)
        self.body.angular_velocity *= 1-(3 * dt)
        # apply gravity
        self.body.apply_force_at_world_point(Vec2(0, 6000 * dt * self.body.mass),  self.body.position)
        # apply buoyancy
        area, center = calc_boyancy(self.body)
        force = Vec2(0, area * -60 * dt)
        self.body.apply_force_at_world_point(force, center)

        # self.body.velocity = Vec2(0, 0)
        # self.body.angular_velocity = 0

    def draw(self, mouse_pos: Vec2):
        pr.draw_texture_pro(self.texture, 
            (0, 0, self.texture.width, self.texture.height),
            (self.body.position.x, self.body.position.y, self.texture.width * 2, self.texture.height * 2),
            (self.texture.width, self.texture.height),
            self.body.angle * 180 / math.pi,
            pr.WHITE
        )