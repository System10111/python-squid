import math
import random

import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

from human import Human

from utils import calc_boyancy, SHIP_CATEGORY, SHIP_HULL_GROUP


class Ship():
    texture: pr.Texture2D
    body: pm.Body
    humans: list[Human]

    def __init__(self, game_data: dict, position: Vec2, space: pm.Space, decks: list[tuple[float, float]]):
        self.texture = game_data["textures"]["boat"]
        self.body = pm.Body()
        self.body.position = position
        hull_size = Vec2(self.texture.width*1.8, self.texture.height*1.9)
        # body_shape = pm.Poly.create_box(self.body, hull_size, 0)
        body_shape = pm.Poly(self.body, [
            (-hull_size.x/2, hull_size.y/2), 
            (-hull_size.x/2, -hull_size.y*0.4/2),
            (hull_size.x/2, hull_size.y/2),
            (hull_size.x/2, -hull_size.y*0.4/2)
        ])
        body_shape.density = 0.001
        body_shape.friction = 5
        body_shape.filter = pm.ShapeFilter(group=SHIP_HULL_GROUP, categories=SHIP_CATEGORY)

        weight_shape = pm.Poly(self.body, [
            (-hull_size.x/5, hull_size.y*2/8), 
            (-hull_size.x/5, hull_size.y*3/8),
            (hull_size.x/5, hull_size.y*3/8),
            (hull_size.x/5, hull_size.y*2/8)
        ])
        weight_shape.density = 0.1
        weight_shape.filter = pm.ShapeFilter(group=SHIP_HULL_GROUP, categories=SHIP_CATEGORY)

        space.add(self.body, body_shape, weight_shape)

        self.humans = []
        for i in range(random.randint(2, 4)):
            self.humans.append(
                Human(game_data, 
                    Vec2(position.x - hull_size.x/2.2 + random.random() * hull_size.x*0.8, 
                        position.y - hull_size.y/2), 
                space)
            )
    
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
        for human in self.humans:
            human.update(dt)
            
    def draw(self, mouse_pos: Vec2):
        for human in self.humans:
            human.draw(mouse_pos)
        pr.draw_texture_pro(self.texture, 
            (0, 0, self.texture.width, self.texture.height),
            (self.body.position.x, self.body.position.y, self.texture.width * 2, self.texture.height * 2),
            (self.texture.width, self.texture.height),
            self.body.angle * 180 / math.pi,
            pr.WHITE
        )