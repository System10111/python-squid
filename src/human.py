import math
import random

import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

HUMAN_GROUP = 30
HUMAN_CATEGORY = 0b10000
from squid import SQUID_SHAPE_GROUP, SQUID_CATEGORY
from utils import calc_boyancy

# sometimes the humans spaz out and turn around too quickly - this is a hard fix to prevent that
turnaround_cooldown = 0.5
max_breath = 10

class Human():
    texture: pr.Texture2D
    animation_data: dict
    cur_animation: str
    anim_time: float
    facing_right: bool
    state: str
    state_time: float
    turnaround_time: float

    human_size: Vec2

    breath: float

    def __init__(self, game_data: dict, position: Vec2, space: pm.Space):
        self.texture = game_data["textures"]["guy2"]
        self.animation_data = game_data["animation_data"]["guy2"]
        self.cur_animation = "neutral"
        self.anim_time = 0
        self.facing_right = random.choice([True, False])
        self.state = "idle"
        self.state_time = random.random() * 4 + 2.0
        self.turnaround_time = 0
        self.breath = max_breath

        self.body = pm.Body()
        self.body.position = position
        human_size = Vec2(5*2, 8*2)
        self.human_size = human_size
        body_shape = pm.Poly.create_box(self.body, human_size, 0)
        body_shape.mass = 0.1
        body_shape.friction = 5
        body_shape.filter = pm.ShapeFilter(group=HUMAN_GROUP, categories=HUMAN_CATEGORY)

        space.add(self.body, body_shape)

    def update(self, dt: float):
        # apply drag
        self.body.velocity *= 1-(1 * dt)
        self.body.angular_velocity *= 1-(3 * dt)
        # apply gravity
        self.body.apply_force_at_world_point(Vec2(0, 6000 * dt * self.body.mass),  self.body.position)

        # apply buoyancy
        buo_area, buo_center = calc_boyancy(self.body)
        self.body.apply_force_at_world_point(Vec2(0, -10 * dt * buo_area * (0.1 if self.state == "dead" else 1)), buo_center)

        if self.body.position.y > 5:
            self.breath -= dt
            if self.breath <= 0:
                self.breath = 0
                self.state = "dead"
                self.state_time = 99999
                self.cur_animation = "dead"
        else:
            self.breath = min(self.breath + dt, max_breath)

        if self.state == "dead":
            return

        # check at two points if we're on the ground
        landed_left = len(self.body.space.bb_query(
                    pm.BB(self.body.position.x + self.human_size.x/2 - 1, 
                        self.body.position.y + self.human_size.y/2 - 1, 
                        self.body.position.x + self.human_size.x/2 + 1, 
                        self.body.position.y + self.human_size.y/2 + 1
                    ), shape_filter=pm.ShapeFilter(group=HUMAN_GROUP))) > 0

        landed_right = len(self.body.space.bb_query(
                    pm.BB(self.body.position.x - self.human_size.x/2 - 1, 
                        self.body.position.y + self.human_size.y/2 - 1, 
                        self.body.position.x - self.human_size.x/2 + 1, 
                        self.body.position.y + self.human_size.y/2 + 1
                    ), shape_filter=pm.ShapeFilter(group=HUMAN_GROUP))) > 0

        self.turnaround_time -= dt
        self.anim_time += dt * 5
        anim = [a for a in self.animation_data["meta"]["frameTags"] if a["name"] == self.cur_animation][0]
        if self.anim_time >= anim["to"] - anim["from"] + 1:
            self.anim_time -= anim["to"] - anim["from"] + 1

        self.state_time -= dt
        if self.state_time < 0:
            self.state_time = random.random() * 4 + 2.0
            self.state = "walk" if self.state == "idle" else "idle"
            if (landed_left or landed_right) and abs(self.body.angle * 180 / math.pi) < 30:
                if random.random() > 0.45 and self.turnaround_time <= 0:
                    self.facing_right = not self.facing_right
                    self.turnaround_time = turnaround_cooldown
        
        # cast a "ray" to check if we see the squid
        sight_range = 50
        if len(self.body.space.bb_query(
            pm.BB(
                self.body.position.x if self.facing_right else (self.body.position.x - sight_range),
                self.body.position.y - 1,
                (self.body.position.x + sight_range) if self.facing_right else self.body.position.x,
                self.body.position.y + 1
            ), shape_filter=pm.ShapeFilter(group=HUMAN_GROUP, mask=SQUID_CATEGORY))) > 0:
            self.state = "run"
            if self.turnaround_time <= 0:
                self.facing_right = not self.facing_right # run away from squid
                self.turnaround_time = turnaround_cooldown
            self.state_time = 10 + random.random() * 10

        if (not landed_left and not landed_right) or abs(self.body.angle * 180 / math.pi) > 60:
            # we're in the air, we panic and flail
            self.state = "run"
            self.state_time = 10 + random.random() * 10

        # correct rotation if only one foot is on the ground
        if landed_left != landed_right and abs(self.body.angle) > 30 * 180 / math.pi:
            self.body.angle *= 1.0 - (5.0 * dt)

        if self.state == "idle":
            self.cur_animation = "neutral"
        elif self.state == "walk" or self.state == "run":
            self.cur_animation = "walk" if self.state == "walk" else "run"
            speed = 10 if self.state == "walk" else 20
            if self.facing_right:
                if landed_left:
                    self.body.position += Vec2(1, 0).rotated(self.body.angle) * speed * dt
                else:
                    if self.state == "run":
                        if self.turnaround_time <= 0:
                            self.facing_right = not self.facing_right
                            self.turnaround_time = turnaround_cooldown
                    else:
                        self.state_time = 0
            else:
                if landed_right:
                    self.body.position += Vec2(1, 0).rotated(self.body.angle) * -speed * dt
                else:    
                    if self.state == "run":
                        if self.turnaround_time <= 0:
                            self.facing_right = not self.facing_right
                            self.turnaround_time = turnaround_cooldown
                    else:
                        self.state_time = 0

    def draw(self, mpos: Vec2):
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

