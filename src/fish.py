import math
import random

import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

from utils import SQUID_SHAPE_GROUP, SQUID_CATEGORY, FISH_CATEGORY, FISH_GROUP

class Fish():
    texture: pr.Texture2D
    animation_data: dict
    cur_animation: str
    anim_time: float
    facing_right: bool
    state: str
    state_time: float

    fish_size: Vec2

    def __init__(self, game_data: dict, position: Vec2, space: pm.Space):
        self.texture = game_data["textures"]["fish"]
        self.animation_data = game_data["animation_data"]["fish"]
        self.cur_animation = "swim"
        self.anim_time = 0
        self.facing_right = random.choice([True, False])
        self.state = "idle"
        self.state_time = random.random() * 4 + 2.0

        self.body = pm.Body()
        self.body.game_object = self
        self.body.position = position
        fish_size = Vec2(16*2, 8*2)
        self.human_size = fish_size
        body_shape = pm.Poly.create_box(self.body, fish_size, 0)
        body_shape.mass = 0.2
        body_shape.friction = 5
        body_shape.filter = pm.ShapeFilter(group=FISH_GROUP, categories=FISH_CATEGORY)

        space.add(self.body, body_shape)

    def update(self, dt: float):
        if self.state == "eaten":
            return
        # apply drag
        self.body.velocity *= 1-(1 * dt)
        self.body.angle = 0

        self.anim_time += dt * {"idle": 1, "swim": 3, "run": 5}[self.state] 
        anim = [a for a in self.animation_data["meta"]["frameTags"] if a["name"] == self.cur_animation][0]
        if self.anim_time >= anim["to"] - anim["from"] + 1:
            self.anim_time -= anim["to"] - anim["from"] + 1

        self.state_time -= dt
        if self.state_time < 0:
            self.state_time = random.random() * 4 + 2.0
            self.state = "swim" if self.state == "idle" else "idle"
            if random.random() > 0.45:
                self.facing_right = not self.facing_right
        
        # cast a "ray" to check if we see the squid
        sight_range = 50
        if self.body.space is not None and len(self.body.space.bb_query(
            pm.BB(
                self.body.position.x if self.facing_right else (self.body.position.x - sight_range),
                self.body.position.y - 1,
                (self.body.position.x + sight_range) if self.facing_right else self.body.position.x,
                self.body.position.y + 1
            ), shape_filter=pm.ShapeFilter(group=FISH_GROUP, mask=FISH_CATEGORY))) > 0:
            self.state = "run"
            if self.turnaround_time <= 0:
                self.facing_right = not self.facing_right # run away from squid
            self.state_time = 10 + random.random() * 10

        if self.state == "idle":
            self.cur_animation = "swim"
        elif self.state == "swim" or self.state == "run":
            self.cur_animation = self.state
            speed = 10 if self.state == "swim" else 20
            if self.facing_right:
                self.body.position += Vec2(1, 0).rotated(self.body.angle) * speed * dt
            else:
                self.body.position += Vec2(1, 0).rotated(self.body.angle) * -speed * dt

    def draw(self, mpos: Vec2):
        if self.state == "eaten":
            return
        anims = self.animation_data["meta"]["frameTags"]
        anim = [a for a in anims if a["name"] == self.cur_animation][0]
        frame_n = anim["from"] + math.floor(self.anim_time)
        frame_data = self.animation_data["frames"][frame_n]
        wdt = frame_data["frame"]["w"]
        hgt = frame_data["frame"]["h"]
        
        pr.draw_texture_pro(self.texture, 
            (frame_data["frame"]["x"], 
            frame_data["frame"]["y"], 
            -wdt if self.facing_right else wdt, 
            hgt),
            (self.body.position.x, self.body.position.y, wdt * 2, hgt * 2),
            (wdt, hgt),
            self.body.angle * 180 / math.pi,
            pr.WHITE)

