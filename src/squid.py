import math

import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

# a pose is a list of lists of tuples
# the elements of the outer list are the tentacles
# the elements of the inner list are the segments of the tentacles
# the first float of the tuple is the angle of the segment
# the second float of the tuple is the strength with which to pull the segment to the angle
Pose = list[list[float]]

SQUID_SHAPE_GROUP = 1
SQUID_CATEGORY = 0b100
N_TENTACLES = 4
N_TENTACLE_SEGMENTS = 5

N_LTENTACLES = 2
N_LTENTACLE_SEGMENTS = 7

N_BODY_SEGMENTS = 4

DEFAULT_POSE: Pose = [[(0) for j in range(N_TENTACLE_SEGMENTS)] for i in range(N_TENTACLES)]
PRE_PUSH_POSE: Pose = [[
        [
            90 * (2*math.pi/360) * [-1, -0.8, 0.8, 1][i],
            -10 * (2*math.pi/360) * (1 if i >= 2 else -1),
            -40 * (2*math.pi/360) * (1 if i >= 2 else -1),
            -10 * (2*math.pi/360) * (1 if i >= 2 else -1),
            -10 * (2*math.pi/360) * (1 if i >= 2 else -1)
        ][j]
        for j in range(N_TENTACLE_SEGMENTS)
    ] for i in range(N_TENTACLES)]
BALANCE_POSE: Pose = [[
        [
            90 * (2*math.pi/360) * [-1, -0.8, 0.8, 1][i],
            -10 * (2*math.pi/360) * [-1, -0.8, 0.8, 1][i],
            -40 * (2*math.pi/360) * (1 if i >= 2 else -1),
            20 * (2*math.pi/360) * (1 if i >= 2 else -1),
            20 * (2*math.pi/360) * (1 if i >= 2 else -1)
        ][j]
        for j in range(N_TENTACLE_SEGMENTS)
    ] for i in range(N_TENTACLES)]
DEFAULT_DAMPING = 1500

# Class for the main character - the squid
class Squid():
    body: pm.Body
    body_tip: pm.Body
    body_texture: pr.Texture2D
    tentacle_texture: pr.Texture2D
    ltentacle_texture: pr.Texture2D
    body_segments: list[tuple[pm.Body, pm.DampedRotarySpring, pm.RotaryLimitJoint]]
    tentacles: list[list[tuple[pm.Body, pm.DampedRotarySpring, pm.SimpleMotor]]]
    ltentacles: list[list[tuple[pm.Body, pm.DampedRotarySpring, pm.SimpleMotor]]]
    # cur_anim: Animation = None
    cur_pose: Pose = DEFAULT_POSE
    anim_speed = 1.0
    anim_time = 0.0

    caught: list

    def __init__(self, game_data: dict, position: Vec2, space: pm.Space):
        base_segment_size = Vec2(32, 16)
        self.body_texture = game_data["textures"]["squid_body"]
        self.tentacle_texture = game_data["textures"]["squid_tentacle"]
        self.ltentacle_texture = game_data["textures"]["squid_ltentacle"]
        # create body
        self.body = pm.Body()
        self.body.position = position
        body_shape = pm.Poly.create_box(self.body, base_segment_size, 1.0)
        body_shape.mass = 20.0
        body_shape.friction = 0.1
        body_shape.filter = pm.ShapeFilter(group=SQUID_SHAPE_GROUP, categories=SQUID_CATEGORY)

        space.add(self.body, body_shape)

        # segment the body so it acts more like a soft body
        last_body = self.body
        self.body_segments = []
        for i in range(1, N_BODY_SEGMENTS):
            scl = [1.0, 0.80, 0.80, 0.90][i]
            b_body = pm.Body()
            b_body.position = last_body.position + Vec2(0, base_segment_size.y/2)
            b_shape = pm.Poly.create_box(b_body, (base_segment_size.x * scl, base_segment_size.y), 1.0)
            b_shape.mass = 0.3 * scl
            b_shape.friction = 0.0
            b_shape.filter = pm.ShapeFilter(group=SQUID_SHAPE_GROUP, categories=SQUID_CATEGORY)
            b_joint = pm.PivotJoint(last_body, b_body, (0, -base_segment_size.y/2), (0, base_segment_size.y/2))

            b_rotary_spring = pm.DampedRotarySpring(last_body, b_body, 0, 20000 * scl, 1500)

            b_rotary_limit = pm.RotaryLimitJoint(last_body, b_body, 
            -9 if i > 1 else -0.5, 
            9 if i > 1 else 0.5
            )

            last_body = b_body
            space.add(b_body, b_shape, b_joint, b_rotary_spring, b_rotary_limit)

            self.body_segments.append((b_body, b_rotary_spring, b_rotary_limit))

        self.body_tip = last_body

        # create tentacles
        self.tentacles = []
        for i, x_prc in enumerate([-1.0, -0.33, 0.33, 1.0]):
            # each tentacle is a list of tuples for each segment (body, constraint)
            tentacle = []
            last_body = self.body
            last_anchor = (base_segment_size.x * 0.40 * x_prc, base_segment_size.y/2)
            for j in range(N_TENTACLE_SEGMENTS):
                t_size = Vec2(7 - j, 20)
                t_body = pm.Body()
                t_body.position = last_body.position + last_anchor + Vec2(0, t_size.y/2)
                t_shape = pm.Poly.create_box(t_body, t_size, 1.0)
                t_shape.mass = 1.0 - j * 0.15
                t_shape.friction = 0.1
                t_shape.filter = pm.ShapeFilter(group=SQUID_SHAPE_GROUP, categories=SQUID_CATEGORY)
                t_joint = pm.PivotJoint(last_body, t_body, last_anchor, (0, -t_size.y/2))
                (angle, strength) = (DEFAULT_POSE[i][j], 5000)
                
                str_mul = [1.0, 0.5, 0.3, 0.2, 0.1, 0.0][j]
                t_rotary_spring = pm.DampedRotarySpring(last_body, t_body, angle, strength * str_mul, DEFAULT_DAMPING * str_mul)

                # limit the angle of the tentacle segment
                t_rotary_limit = pm.RotaryLimitJoint(last_body, t_body, 
                    -90 if i >= 2 else -60, 
                    60 if i >= 2 else 90
                )

                t_motor = pm.SimpleMotor(last_body, t_body, 0.0)
                t_motor.max_force = 15000.0
                tentacle.append((t_body, t_rotary_spring, t_motor))
                space.add(t_body, t_shape, t_joint, t_rotary_spring, t_motor, t_rotary_limit)

                last_body = t_body
                last_anchor = (0, t_size.y/2)
            
            self.tentacles.append(tentacle)

        # create long tentacles
        self.ltentacles = []
        for i, x_prc in enumerate([-1.0, 1.0]):
            tentacle = []
            last_body = self.body
            last_anchor = (base_segment_size.x * 0.50 * x_prc, base_segment_size.y/2)
            for j in range(N_LTENTACLE_SEGMENTS):
                is_last = j == N_LTENTACLE_SEGMENTS - 1

                t_size = Vec2(5 - int(j/2), 20) if not is_last else Vec2(8, 16)
                t_body = pm.Body()
                t_body.position = last_body.position + last_anchor + Vec2(0, t_size.y/2)
                t_shape = pm.Poly.create_box(t_body, t_size, 1.0)
                t_shape.mass = (0.8 - j * 0.10 if not is_last else 0.8) * 0.75
                t_shape.friction = 0.05 if not is_last else 30
                t_shape.filter = pm.ShapeFilter(group=SQUID_SHAPE_GROUP, categories=SQUID_CATEGORY)
                t_joint = pm.PivotJoint(last_body, t_body, last_anchor, (0, -t_size.y/2))
                (angle, strength) = (0, 1000)

                str_mul = [1.0, 0.8, 0.5, 0.4, 0.4, 0.4, 0.4, 0.0][j]
                t_rotary_spring = pm.DampedRotarySpring(last_body, t_body, angle, strength * str_mul, DEFAULT_DAMPING * str_mul)

                # limit the angle of the tentacle segment
                t_rotary_limit = pm.RotaryLimitJoint(last_body, t_body, 
                    (-90 if i >= 1 else -60) * str_mul, 
                    (60 if i >= 1 else 90) * str_mul
                )

                t_motor = pm.SimpleMotor(last_body, t_body, 0.0)
                t_motor.max_force = 0.0

                tentacle.append((t_body, t_rotary_spring, t_motor))
                space.add(t_body, t_shape, t_joint, t_rotary_spring, t_motor, t_rotary_limit)

                last_body = t_body
                last_anchor = (0, t_size.y/2)


            self.ltentacles.append(tentacle)

    def update(self, dt: float):
        # set the tentacles' motor rates depending on the animation and the current angle between segments
        for i, tentacle in enumerate(self.tentacles):
            last_body = self.body
            for j, (t_body, t_rotary_spring, t_motor) in enumerate(tentacle):
                cur_angle = (last_body.angle - t_body.angle)
                rand_angle_diff = 5 * (2*math.pi/360) * math.sin(self.anim_time * 9 / (5.0 - j) + j + (1009 * i))
                want_angle = self.cur_pose[i][j] + rand_angle_diff
                ang_diff = (want_angle - cur_angle) * 2
                # the biggest prime below 1000 is 

                if abs(ang_diff) < 0.05:
                    ang_diff = 0.0
                elif abs(ang_diff) < 0.3:
                    ang_diff = 0.3 * (ang_diff / abs(ang_diff))
                elif abs(ang_diff) > 0.6:
                    ang_diff = 0.6 * (ang_diff / abs(ang_diff))
                last_body = t_body

                t_motor.rate = ang_diff * 3
        
        # add drag to the end of the long tentacles
        for i, tentacle in enumerate(self.ltentacles):
            last_body = self.body
            for j, (t_body, t_rotary_spring, t_motor) in enumerate(tentacle):
                # if the relative angle between the last segment and the current one is more than pi
                # add 2pi or -2pi to the resting angle to release the tension when the tentacle gets wound up
                rel_angle = (last_body.angle - t_body.angle)
                if rel_angle > math.pi:
                    t_body.angle += 2 * math.pi
                elif rel_angle < -math.pi:
                    t_body.angle -= 2 * math.pi
            tentacle[-1][0].velocity *= 1-dt


        bodies = [self.body] + \
                [s[0] for s in self.body_segments] + \
                [t[0] for sublist in self.tentacles for t in sublist] + \
                [t[0] for sublist in self.ltentacles for t in sublist]
        
        # apply a force to the squid if it is above the water
        for b in bodies:
            if b.position.y < 0:
                b.apply_force_at_world_point((0, 10000 * dt * b.mass), b.position)

        # apply angular drag to the squid
        self.body.angular_velocity *= 1 - dt * 0.5

        self.anim_time += dt

    def draw(self, mpos: Vec2):
        """Draw the squid"""
        
        # draw the base segment
        pr.draw_texture_pro(self.body_texture, 
            (0, self.body_texture.height * 3/4, self.body_texture.width, self.body_texture.height/4),
            (self.body.position.x,
                self.body.position.y, 
                self.body_texture.width*2, 
                self.body_texture.height*2/4),
            (self.body_texture.width*2/2, self.body_texture.height*2/4/2),
            self.body.angle * 180 / math.pi,
            pr.WHITE
        )

        # draw the eyes
        for eye_center in [(-9, -3), (9, -3)]:
            eye_center = self.body.local_to_world(eye_center)
            dir_to_mouse = (mpos - eye_center).normalized()
            eye_center += dir_to_mouse * 2
            pr.draw_rectangle_pro(
                (eye_center.x, eye_center.y, 4, 4),
                (2, 2),
                self.body.angle * 180 / math.pi,
                pr.BLACK
            )

        # draw the other body segments
        for i, seg in enumerate(self.body_segments):
            seg_body = seg[0]

            pr.draw_texture_pro(self.body_texture,
                (0, self.body_texture.height * (2-i)/4, self.body_texture.width, self.body_texture.height/4),
                (seg_body.position.x,
                    seg_body.position.y, 
                    self.body_texture.width*2, 
                    self.body_texture.height*2/4),
                (self.body_texture.width*2/2, self.body_texture.height*2/4/2),
                seg_body.angle * 180 / math.pi,
                pr.WHITE
            )

        # draw the long tentacles
        for i, tentacle in enumerate(self.ltentacles):
            for j, (t_body, t_rotary_spring, t_motor) in enumerate(tentacle):
                if j < N_LTENTACLE_SEGMENTS - 1:
                    pr.draw_texture_pro(self.ltentacle_texture,
                        (0 if i < 1 else self.ltentacle_texture.width, 
                            (self.ltentacle_texture.height-8) * j / (len(tentacle)-1), 
                            self.ltentacle_texture.width if i < 1 else -self.ltentacle_texture.width, 
                            (self.ltentacle_texture.height-8) / (len(tentacle))-1),
                        (t_body.position.x,
                            t_body.position.y, 
                            self.ltentacle_texture.width*2, 
                            (self.ltentacle_texture.height-8)*2 / (len(tentacle)-1)),
                        (self.ltentacle_texture.width*2/2, (self.ltentacle_texture.height-8)*2/(len(tentacle)-1)/2),
                        t_body.angle * 180 / math.pi,
                        pr.WHITE
                    )
                else: # draw the "hand"
                    pr.draw_texture_pro(self.ltentacle_texture,
                        (0 if i < 1 else self.ltentacle_texture.width, 
                            self.ltentacle_texture.height-8, 
                            self.ltentacle_texture.width if i < 1 else -self.ltentacle_texture.width, 
                            8),
                        (t_body.position.x,
                            t_body.position.y, 
                            self.ltentacle_texture.width*2, 
                            16),
                        (self.ltentacle_texture.width*2/2, 16/2),
                        t_body.angle * 180 / math.pi,
                        pr.WHITE
                    )
                

        # draw the tentacles
        for i, tentacle in enumerate(self.tentacles):
            for j, (t_body, t_rotary_spring, t_motor) in enumerate(tentacle):
                # the tentacle texture is separated into segments of 5 pixels
                # the texture should be horizontally flipped if the tentacle is on the right side of the squid
                pr.draw_texture_pro(self.tentacle_texture,
                    (0 if i < 2 else self.tentacle_texture.width, 
                        self.tentacle_texture.height * j / len(tentacle), 
                        self.tentacle_texture.width if i < 2 else -self.tentacle_texture.width, 
                        self.tentacle_texture.height / len(tentacle)),
                    (t_body.position.x,
                        t_body.position.y, 
                        self.tentacle_texture.width*2, 
                        self.tentacle_texture.height*2 / len(tentacle)),
                    (self.tentacle_texture.width*2/2, self.tentacle_texture.height*2/len(tentacle)/2),
                    t_body.angle * 180 / math.pi,
                    pr.WHITE
                )

    def set_pose(self, pose: Pose = None):
        """
        Sets on the squid's tentacles.
        """
        pose = DEFAULT_POSE if pose is None else pose

        for i, tentacle in enumerate(self.tentacles):
            if i >= len(pose) or pose[i] is None:
                continue
            t_pose = pose[i]
            for j, (t_body, t_constraint, t_motor) in enumerate(tentacle):
                if len(t_pose) <= j or t_pose[j] is None:
                    continue
                t_constraint.rest_angle = t_pose[j]
        
        self.cur_pose = pose

    def get_spread(self) -> float:
        """Returns some value representing the total amount of deviation of tentacles from the center
        For a given tentacle, if it is on the left side, 
        then we add value to the total if the angle between the body and the first segment
        is facing away from the center
        and subtract if it is facing towards the center, vice versa if it is on the right side.
        It tapers off as the angle gets bigger - having a twice as big angle will contribute less than twice as much.
        This is to encourage to spread both sets of tantacles rather than have them all facing one direction from innertia.
        """

        spread = 0.0
        for i, tentacle in enumerate(self.tentacles):
            t_body, t_constraint, t_motor = tentacle[0]
            angle = t_body.angle - self.body.angle
            if i < len(self.tentacles) / 2:
                # left side
                if angle > 0:
                    spread += angle * angle
                else:
                    spread -= angle * angle
            else:
                # right side
                if angle < 0:
                    spread += angle * angle
                else:
                    spread -= angle * angle
        return spread

    def reach(self, pos: tuple[float, float]):
        """
        Apply force to one of the ends of the squid's 
        long tentacles to get it to go to the given position
        """
    	# find the distances to the given position from each of the long tentacles' ends
        ldist = (self.ltentacles[0][-1][0].position - pos).length
        rdist = (self.ltentacles[1][-1][0].position - pos).length
        # find the distance from the point to the squid central's axis
        squid_perp = Vec2(1, 0).rotated(self.body.angle)
        axis_dist = (pos - self.body.position).dot(squid_perp)
        # add a factor ralating to the distance to the squid's axis
        ldist *= (1/(1+math.pow(math.e, -axis_dist/100))) + 0.5

        closer = self.ltentacles[0 if ldist < rdist else 1][-1][0]
        force = (pos - closer.position).normalized() * 500
        point = closer.local_to_world((0, 0))
        closer.apply_force_at_world_point(force, point)

        # apply equal and opposite force to the squid's body to prevent it from moving
        # self.body.apply_force_at_world_point(-force, point)




    

# def swim_anim(time: float, dt: float) -> tuple[Pose, list[Callable]]:
#     """Swim animation"""
#     # loop every 4 seconds
#     time = time % 4.0

#     # the animation is divided into 4 parts:
#     # 1. Curl tentacles
#     # ,-S-,
#     # '- -'
#     # 2. Expand tentacles to the side
#     # ---S---
#     # 3. Push off
#     #   S
#     #  | |
#     #  | |
#     # 4. Stay like this, while traveling forwards

#     # 1. Curl tentacles
#     if time < 1.2:
#         return [
#             [
#                 (-time*1.6, 300000), 
#                 (time*1.2, 300000), 
#                 (time*1.3, 200000), 
#                 (time*0.9, 100000), (0, 30000)
#             ],
#             [
#                 (-time*1.5, 300000), 
#                 (time*1.1, 300000), 
#                 (time*1.2, 200000), 
#                 (time*0.8, 100000), (0, 30000)
#             ],
#             [
#                 (time*1.5, 300000), 
#                 (-time*1.1, 300000), 
#                 (-time*1.2, 200000), 
#                 (-time*0.8, 100000), (0, 30000)
#             ],
#             [
#                 (time*1.6, 300000), 
#                 (-time*1.2, 300000), 
#                 (-time*1.3, 200000), 
#                 (-time*0.9, 100000), (0, 30000)
#             ],
#         ], []
#     # 2. Expand tentacles to the side
#     elif time < 2.2:
#         return [
#             [
#                 (-1.2*1.6, 400000), 
#                 (0, 200000), (0, 20000), (0, 10000), (0, 30000)
#             ],
#             [
#                 (-1.2*1.5, 400000), 
#                 (0, 200000), (0, 20000), (0, 10000), (0, 30000)
#             ],
#             [
#                 (1.2*1.5, 400000), 
#                 (0, 200000), (0, 20000), (0, 10000), (0, 30000)
#             ],
#             [
#                 (1.2*1.6, 400000), 
#                 (0, 200000), (0, 20000), (0, 10000), (0, 30000)
#             ],
#         ], []
#     # 3. Push off
#     elif time < 2.7:
#         events = [] 
#         if time < 2.4 and time+dt >= 2.4:
#             events.append(lambda squid: squid.body.apply_impulse_at_local_point((0, -750)))
        
#         return [
#             [
#                 (0, 200000), 
#                 (0, 200000), (0, 100000), (0, 100000), (0, 100000)
#             ],
#             [
#                 (0, 200000), 
#                 (0, 200000), (0, 100000), (0, 100000), (0, 100000)
#             ],
#             [
#                 (0, 200000), 
#                 (0, 200000), (0, 100000), (0, 100000), (0, 100000)
#             ],
#             [
#                 (0, 200000), 
#                 (0, 200000), (0, 100000), (0, 100000), (0, 100000)
#             ],
#         ], events
#     # 4. Stay like this, while traveling forwards
#     else:
#         return [
#             [
#                 (0, 5000000), 
#                 (0, 1300000), (0, 1000000), (0, 7000000), (0, 500000)
#             ] for _ in range(4)
#         ], []