import os
import json
import random

import math
import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

from squid import Squid, DEFAULT_POSE, PRE_PUSH_POSE, BALANCE_POSE
from ship import Ship
from fish import Fish, FISH_GROUP, FISH_CATEGORY

WALL_CATEGORY = 0b10

class RLDrawOptions(pm.SpaceDebugDrawOptions):
    """ A class that implements the pymunk debug draw options interface for pyray """
    def __init__(self):
        super().__init__()

    def draw_circle(self, pos, angle, radius, outline_color, fill_color):
        col = pr.Color(int(fill_color.r), int(fill_color.g), int(fill_color.b), int(fill_color.a))
        pr.draw_circle(int(pos.x), int(pos.y), radius, col)
        line_end = Vec2(radius, 0).rotated(angle) + pos
        pr.draw_line(int(pos.x), int(pos.y), int(line_end.x), int(line_end.y), col)

    def draw_segment(self, a, b, color):
        col = pr.Color(int(color.r), int(color.g), int(color.b), int(color.a))
        pr.draw_line(int(a.x), int(a.y), int(b.x), int(b.y), col)

    def draw_fat_segment(self, a, b, radius, outline_color, fill_color):
        col = pr.Color(int(fill_color.r), int(fill_color.g), int(fill_color.b), int(fill_color.a))
        pr.draw_line(int(a.x), int(a.y), int(b.x), int(b.y), col)

    def draw_polygon(self, verts, radius, outline_color, fill_color):
        col = pr.Color(int(fill_color.r), int(fill_color.g), int(fill_color.b), int(fill_color.a))
        for i in range(len(verts) - 1):
            pr.draw_line(int(verts[i].x), int(verts[i].y), int(verts[i+1].x), int(verts[i+1].y), col)
        pr.draw_line(int(verts[-1].x), int(verts[-1].y), int(verts[0].x), int(verts[0].y), col)

    def draw_dot(self, size, pos, color):
        col = pr.Color(int(color.r), int(color.g), int(color.b), int(color.a))
        pr.draw_circle(int(pos.x), int(pos.y), size, col)

def load_walls(file: str) -> list[float]:
    """ 
    Load the walls from a json file
    The file should have to following structure:
    {
        "walls": [
            [x1, y1, x2, y2],
            [x1, y1, x2, y2],
            ...
        ]
    }
    """
    with open(file, "r") as f:
        data = json.load(f)
        walls = data["walls"]
        return walls
    

def main():
    window_size = Vec2(1280, 720)

    # Create a window with a size of 1280x720 pixels
    pr.init_window(int(window_size.x), int(window_size.y), "Squid")
    pr.set_target_fps(60)
 

    debug_options = {
        "draw_collision": False,
        "wall_placement": False,
    }

    game_data = {
        "textures" : {
            "level": pr.load_texture(os.path.join("res", "level.png")),
            "squid_body": pr.load_texture(os.path.join("res", "squid-body.png")),
            "squid_tentacle": pr.load_texture(os.path.join("res", "squid-tentacle.png")),
            "squid_ltentacle": pr.load_texture(os.path.join("res", "squid-ltentacle.png")),
            "guy1": pr.load_texture(os.path.join("res", "guy1.png")),
            "guy2": pr.load_texture(os.path.join("res", "guy2.png")),
            "boat": pr.load_texture(os.path.join("res", "boat.png")),
            "water": pr.load_texture(os.path.join("res", "water.png")),
            "fish": pr.load_texture(os.path.join("res", "fish.png")),
        },
        "animation_data": {
            "guy2": json.load(open(os.path.join("res", "guy2.json"), "r")),
            "water": json.load(open(os.path.join("res", "water.json"), "r")),
            "fish": json.load(open(os.path.join("res", "fish.json"), "r")),
        }
    }

    level_rect = (0, -380, game_data["textures"]["level"].width, game_data["textures"]["level"].height)

    # Create a camera
    camera = pr.Camera2D((0, 0), (0, 0), 0, 1)
    camera.offset = window_size / 2
    camera.zoom = 2.5

    # Setup physics
    draw_options = RLDrawOptions()
    draw_options.shape_dynamic_color = (0, 0, 0, 255)
    space = pm.Space()
    space.gravity = (0, 0)
    # space.damping = 0.01
    
    # Create the squid
    squid = Squid(game_data, Vec2(300, 100), space) 

    # Create the level
    walls = load_walls(os.path.join("res", "walls.json"))
    #add all the walls to the physics space
    for wall in walls:
        shape = pm.Segment(space.static_body, (wall[0], wall[1]), (wall[2], wall[3]), 0)
        shape.friction = 0.1
        shape.filter = pm.ShapeFilter(categories=WALL_CATEGORY)
        space.add(shape)
    
    # setup gameplay variables
    push_buildup = 0.0
    MAX_PUSH_BUILDUP = 1.0
    good_push = False

    game_objects = [squid]

    game_objects.append(Ship(game_data, squid.body.position + Vec2(30, -100), space, []))

    # spawn boats
    ship_x = 100
    while ship_x < 2100:
        ship_x += random.randint(200, 500)
        ship_y = -4
        game_objects.append(Ship(game_data, Vec2(ship_x, ship_y), space, walls))
    
    ship_x = 4500
    while ship_x < 7200:
        ship_x += random.randint(200, 500)
        ship_y = -4
        game_objects.append(Ship(game_data, Vec2(ship_x, ship_y), space, walls))

    water_tiles = [0] * 20

    fish_spawn_cooldown = 0.0
    fish_spawn_cooldown_max = 2.0

    blood_particles = []
    point_particles = []

    point_total = 0

    # Run the game loop
    while not pr.window_should_close():
        dt = pr.get_frame_time()

        mouse_pos = pr.get_screen_to_world_2d(pr.get_mouse_position(), camera)
        mouse_pos = Vec2(mouse_pos.x, mouse_pos.y)
        ### UPDATE ###

        for i in range(0, len(water_tiles)):
            if random.random() < 0.01:
                water_tiles[i] += 1
                if water_tiles[i] >= 3:
                    water_tiles[i] = 0

        # Update the camera
        if pr.is_key_pressed(pr.KEY_F1):
            debug_options["draw_collision"] = not debug_options["draw_collision"]

        if pr.is_key_pressed(pr.KEY_F2):
            debug_options["wall_placement"] = not debug_options["wall_placement"]

        if pr.is_key_down(pr.KEY_T):
            squid.body.apply_force_at_local_point((0, 1000), (0, 0))

        # adding walls
        if debug_options["wall_placement"]:
            if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON):
                # Calculate the position of the mouse in the world
                mouse_pos = pr.get_mouse_position()
                mouse_pos = pr.get_screen_to_world_2d(mouse_pos, camera)
                mouse_pos = Vec2(mouse_pos.x, mouse_pos.y)
                walls.append([mouse_pos.x, mouse_pos.y, 0.0, 0.0])
            elif pr.is_mouse_button_pressed(pr.MOUSE_RIGHT_BUTTON):
                mouse_pos = pr.get_mouse_position()
                mouse_pos = pr.get_screen_to_world_2d(mouse_pos, camera)
                mouse_pos = Vec2(mouse_pos.x, mouse_pos.y)
                walls[-1][2] = mouse_pos.x
                walls[-1][3] = mouse_pos.y
            if pr.is_key_down(pr.KEY_BACKSPACE):
                walls.pop()
            if pr.is_key_down(pr.KEY_S):
                camera.target.y += 10
            if pr.is_key_down(pr.KEY_W):
                camera.target.y -= 10
            if pr.is_key_down(pr.KEY_A):
                camera.target.x -= 10
            if pr.is_key_down(pr.KEY_D):
                camera.target.x += 10
            if pr.is_key_pressed(pr.KEY_ENTER):
                # save the walls to a json file
                data = {"walls": walls}
                with open(os.path.join("res", "walls.json"), "w") as f:
                    json.dump(data, f, indent=4)

        in_water = squid.body.position.y > 0

        # Squid movement
        if True: # Movement enabled
            turn_speed = 1.5
            max_speed = 350

            squid_dir = Vec2(0, 1).rotated(squid.body.angle)
            mouse_dir = mouse_pos - squid.body.position
            mouse_dir = Vec2(mouse_dir.x, mouse_dir.y).normalized()
            angle_diff = -mouse_dir.get_angle_between(-squid_dir)
            mouse_dist = mouse_pos.get_distance(squid.body.position)
            vel_len = squid.body.velocity.length
            vel_dir = Vec2(squid.body.velocity.x, squid.body.velocity.y).normalized()

            scl_angle_diff = (min(abs(angle_diff)*10, 1) * (angle_diff / abs(angle_diff))) if angle_diff != 0 else 0

            if in_water:
                # turn_speed *= 1 - 0.6 * min(vel_len / 100, 1)
                
                # slow down the squid in the direction perpendicular to its facing
                perp = Vec2(-squid_dir.y, squid_dir.x)
                squid.body.velocity -= perp * squid.body.velocity.dot(perp) * dt * 5

                squid.body.velocity *= 1 - dt*0.2*math.sqrt(max(vel_len, 10)/200)

                # slow down the spin if we are close to the mouse and moving quickly
                squid.body.angular_velocity *= 1 - max(0.8 - (angle_diff*angle_diff)/2*2, 0)*dt*3 * min(vel_len/50, 1)

                # if we're moving quickly, there'll be an aerodynamic correction force, 
                # which will try too keep us facing the direction of movement
                ang_err = -vel_dir.get_angle_between(-squid_dir)
                squid.body.angular_velocity += ang_err * dt * 15 * min(vel_len/100, 1)

                squid.body.angular_velocity *= 1-dt*5

            if pr.is_mouse_button_down(pr.MOUSE_LEFT_BUTTON):
                if good_push:
                    good_push = False
                    push_buildup = min(push_buildup, MAX_PUSH_BUILDUP/4)
                squid.set_pose(PRE_PUSH_POSE)
                push_buildup = min(push_buildup + dt/2, MAX_PUSH_BUILDUP)
                squid.body.angular_velocity += turn_speed * vel_len * 0.001 * scl_angle_diff
                if squid.body.angular_velocity * angle_diff < 0: # they have different signs
                    squid.body.angular_velocity *= 1-(dt*5)

                if pr.is_mouse_button_down(pr.MOUSE_RIGHT_BUTTON):
                    turn_speed *= 12.0
                    squid.set_pose(BALANCE_POSE)
                
                squid.body.angular_velocity += turn_speed * scl_angle_diff/50
                # slow down the squid if it is moving backwards relative to its body
                if squid_dir.dot(vel_dir) > 0.2:
                    squid.body.velocity *= 0.9
        
            else:
                # if we bulid enough push, we do a 'good push'
                if not good_push and push_buildup > 0.1:
                    # add more push the more the squid's tantacles are facing away from the center
                    push_buildup += squid.get_spread() * 0.08
                    good_push = True
                    if pr.is_mouse_button_down(pr.MOUSE_RIGHT_BUTTON):
                        # we can prevent the push by holding the right mouse button
                        push_buildup = 0.0
                        good_push = False
                        # since this also acts as a break, we also slow down the squid
                        squid.body.velocity *= 0.75
                        squid.body.angular_velocity *= 0.75


                # good push - push the squid in the direction it is facing while adding
                # angular velocity to the squid to make it look at the mouse
                if good_push:
                    push_buildup = max(push_buildup - dt * max(vel_len/(0.5*max_speed), 1) / 2, 0.0)
                    # apply angular velocity to the squid
                    squid.body.angular_velocity += turn_speed * scl_angle_diff * push_buildup / 30
                    if squid.body.angular_velocity * angle_diff < 0: # they have different signs
                        squid.body.angular_velocity *= 1-(dt*20)
                    squid.set_pose(DEFAULT_POSE)
                    # apply force to the squid
                    force = push_buildup * 2000 * min(mouse_dist / 50.0, 1.0) * (1 - (min(vel_len/max_speed, 1)))
                    squid.body_tip.apply_force_at_local_point(Vec2(0, -1) * force, (0, -50))
                    # squid.body.velocity += -squid_dir * push_buildup * 100 * min(mouse_dist, 50.0) / 50.0 * dt
                    
                    if push_buildup == 0.0:
                        good_push = False
                    
                    
                else:
                    # neutral
                    squid.body.angular_velocity *= 1-(dt*0.5)
                    push_buildup = max(push_buildup - dt, 0.0)
                    good_push = False            
                    squid.set_pose(DEFAULT_POSE)

            fish_spawn_cooldown -= dt

            if vel_len > 10:
                # spawn some fish
                if (random.random() < 0.01 and fish_spawn_cooldown <= 0.0) or pr.is_key_pressed(pr.KEY_F5):
                    
                    spawn_pos = squid.body.position + (vel_dir * (random.random() * 300 + 300)).rotated(random.random() * 0.5 - 0.25)
                    # check that the fish is not spawning inside a wall,
                    # above the water, or near a lot of other fish
                    in_level = spawn_pos.x > level_rect[0] and \
                        spawn_pos.x < level_rect[0] + level_rect[2] and \
                        spawn_pos.y > level_rect[1] and \
                        spawn_pos.y < level_rect[1] + level_rect[3]
                    if in_level and \
                       not space.bb_query(pm.BB(spawn_pos.x-10, spawn_pos.y-10, spawn_pos.x+10, spawn_pos.y+10), pm.ShapeFilter()) and\
                       not spawn_pos.y < 0 and \
                       not len(space.bb_query(pm.BB(spawn_pos.x-200, spawn_pos.y-200, spawn_pos.x+200, spawn_pos.y+200), 
                        pm.ShapeFilter(categories=FISH_CATEGORY, mask=FISH_CATEGORY))) > 3:
                        fish = Fish(game_data, spawn_pos, space)
                        game_objects.append(fish)
                        fish_spawn_cooldown = fish_spawn_cooldown_max
                    
        # Check if the squid is eating something
        for i, tnt in enumerate([lt[-1][0] for lt in squid.ltentacles]):
            if squid.caught[i] is not None:
                if (squid.caught[i].body.position - squid.body.position).length < 10:
                    squid.caught[i].body.game_object.state = "eaten"
                    # append between 3 and 5 blood particles with random velocity
                    for _ in range(random.randint(3, 5)):
                        vel = Vec2(random.random() * 2 - 1, random.random() * 2 - 1) * 10
                        blood_particles.append((tnt.position, vel, random.random() * 0.3 + 0.5))
                        points = 50 if isinstance(squid.caught[i].body.game_object, Fish) else 100
                        point_particles.append((tnt.position - Vec2(0, 20), points, random.random() * 0.1 + 0.5))
                        point_total += points
                    squid.caught[i] = None

        if not pr.is_mouse_button_down(pr.MOUSE_LEFT_BUTTON) and pr.is_mouse_button_down(pr.MOUSE_RIGHT_BUTTON):
            squid.reach(mouse_pos)

        # Update the physics
        space.step(dt)

        # Update the game objects
        for obj in game_objects:
            obj.update(dt)
        if not debug_options["wall_placement"]:
            camera.target = squid.body.position

        ### DRAWING ###
        pr.begin_drawing()
        pr.clear_background(pr.SKYBLUE)
        pr.begin_mode_2d(camera)

        # Draw the level
        pr.draw_texture_ex(game_data["textures"]["level"], (0, level_rect[1]), 0, 2, pr.WHITE)

        for obj in game_objects:
            obj.draw(mouse_pos)

        # draw the water
        for x in range(int(squid.body.position.x/64) - 10, int(squid.body.position.x/64) + 10):
            frame = water_tiles[x % len(water_tiles)]
            pr.draw_texture_pro(
                game_data["textures"]["water"],
                (32 * frame, 0, 32, 16),
                (x*64, 8, 64, 32),
                (16, 16),
                0,
                pr.WHITE
            )

        # draw blood particles as 4x4 squares
        for i, bp in enumerate(blood_particles):
            pr.draw_rectangle(int(bp[0].x), int(bp[0].y), 4, 4, pr.RED)
            blood_particles[i] = (bp[0] + bp[1] * dt, bp[1] * (1-dt) + Vec2(0, 10 * dt), bp[2] - dt)
            if blood_particles[i][2] <= 0:
                blood_particles.pop(i)
        
        # draw point particles as text
        for i, pp in enumerate(point_particles):
            pr.draw_text(str(pp[1]), int(pp[0].x), int(pp[0].y), 21, pr.BLACK)
            pr.draw_text(str(pp[1]), int(pp[0].x), int(pp[0].y), 20, pr.WHITE)
            point_particles[i] = (pp[0] + Vec2(0, 50 * dt), pp[1], pp[2] - dt)
            if point_particles[i][2] <= 0:
                point_particles.pop(i)

        if debug_options["draw_collision"]:
            space.debug_draw(draw_options)

        if debug_options["wall_placement"]:
            for wall in walls:
                pr.draw_line(int(wall[0]), int(wall[1]), int(wall[2]), int(wall[3]), pr.RED)

        pr.end_mode_2d()
        # Draw the ui
        ui_camera = pr.Camera2D((0, 0), (0, 0), 0, 1)
        pr.begin_mode_2d(ui_camera)

        pr.draw_rectangle(100, 50, 200, 10, pr.GRAY)
        pr.draw_rectangle(102, 52, int(push_buildup/MAX_PUSH_BUILDUP*96 + 0.5), 6, pr.WHITE)
        pr.draw_text("%.3f" % round(squid.body.velocity.length/3, 3) + " km/h", 100, 30, 10, pr.WHITE)
        pr.draw_text("Points: " + str(point_total), 100, 10, 10, pr.WHITE)

        pr.end_mode_2d()
        pr.end_drawing()
    
    # Close the window
    for tex in game_data["textures"].values():
        pr.unload_texture(tex)
    pr.close_window()

if __name__ == "__main__":
    main()
