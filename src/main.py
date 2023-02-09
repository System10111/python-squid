import os
import json

import math
import pyray as pr
import pymunk as pm
from pymunk.vec2d import Vec2d as Vec2

from squid import Squid, DEFAULT_POSE, PRE_PUSH_POSE, BALANCE_POSE


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
        "draw_collision": True
    }

    # Load textures
    guy1 = pr.load_texture(os.path.join("res", "guy1.png"))

    # Create a camera
    camera = pr.Camera2D((0, 0), (0, 0), 0, 1)
    camera.offset = window_size / 2
    camera.zoom = 2.5
    camera.target = Vec2(300, 300)

    # Setup physics
    draw_options = RLDrawOptions()
    draw_options.shape_dynamic_color = (0, 0, 0, 255)
    space = pm.Space()
    space.gravity = (0, 0)
    # space.damping = 0.01
    
    # Create the squid
    squid = Squid(Vec2(300, 300), 
        pr.load_texture(os.path.join("res", "squid-body.png")), 
        pr.load_texture(os.path.join("res", "squid-tentacle.png")),
        pr.load_texture(os.path.join("res", "squid-ltentacle.png")),
        space) 

    # Create the level
    walls = load_walls(os.path.join("res", "walls.json"))
    level = pr.load_texture(os.path.join("res", "test_level.png"))
    #add all the walls to the physics space
    for wall in walls:
        shape = pm.Segment(space.static_body, (wall[0], wall[1]), (wall[2], wall[3]), 0)
        shape.friction = 0.1
        space.add(shape)
    
    # setup gameplay variables
    push_buildup = 0.0
    MAX_PUSH_BUILDUP = 1.0
    good_push = False

    # Run the game loop
    while not pr.window_should_close():
        dt = pr.get_frame_time()

        mouse_pos = pr.get_screen_to_world_2d(pr.get_mouse_position(), camera)
        mouse_pos = Vec2(mouse_pos.x, mouse_pos.y)
        ### UPDATE ###

        # Update the camera
        if pr.is_key_pressed(pr.KEY_F1):
            debug_options["draw_collision"] = not debug_options["draw_collision"]

        if pr.is_key_pressed(pr.KEY_ENTER):
            # save the walls to a json file
            data = {"walls": walls}
            with open(os.path.join("res", "walls.json"), "w") as f:
                json.dump(data, f, indent=4)

        if pr.is_key_down(pr.KEY_T):
            squid.body.apply_force_at_local_point((0, 1000), (0, 0))

        # adding walls
        if False:
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

        # Squid movement
        if True: # movement enabled
            turn_speed = 1.5
            max_speed = 350

            squid_dir = Vec2(0, 1).rotated(squid.body.angle)
            mouse_dir = mouse_pos - squid.body.position
            mouse_dir = Vec2(mouse_dir.x, mouse_dir.y).normalized()
            angle_diff = -mouse_dir.get_angle_between(-squid_dir)
            mouse_dist = mouse_pos.get_distance(squid.body.position)
            vel_len = squid.body.velocity.length
            vel_dir = Vec2(squid.body.velocity.x, squid.body.velocity.y).normalized()

            scl_angle_diff = min(abs(angle_diff)*10, 1) * (angle_diff / abs(angle_diff))


            turn_speed *= 1 - 0.6 * (min(vel_len / 125, 1))
            
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
                    turn_speed *= 9.0
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
                    push_buildup = max(push_buildup - dt, 0.0)
                    good_push = False            
                    squid.set_pose(DEFAULT_POSE)


        if not pr.is_mouse_button_down(pr.MOUSE_LEFT_BUTTON) and pr.is_mouse_button_down(pr.MOUSE_RIGHT_BUTTON):
            squid.reach(mouse_pos)

        # Update the physics
        space.step(dt)

        # Update the squid
        squid.update(dt)
        camera.target = squid.body.position

        ### DRAWING ###
        pr.begin_drawing()
        pr.clear_background(pr.DARKBLUE)
        pr.begin_mode_2d(camera)

        # Draw the level
        pr.draw_texture(level, 0, 0, pr.WHITE)

        # to help with debugging, draw a guy1 every 100 horizontal pixels
        # draw only about 20 of them centered around the squid, so we don't draw too many
        # and slow down the game
        for x in range(int(squid.body.position.x/100) - 10, int(squid.body.position.x/100) + 10):
            pr.draw_texture(guy1, x*100, 0, pr.WHITE)

        squid.draw(mpos=mouse_pos)

        if debug_options["draw_collision"]:
            space.debug_draw(draw_options)

        pr.end_mode_2d()
        # Draw the ui
        ui_camera = pr.Camera2D((0, 0), (0, 0), 0, 1)
        pr.begin_mode_2d(ui_camera)

        pr.draw_rectangle(100, 50, 100, 10, pr.GRAY)
        pr.draw_rectangle(102, 52, int(push_buildup/MAX_PUSH_BUILDUP*96 + 0.5), 6, pr.WHITE)
        pr.draw_text("%.3f" % round(squid.body.velocity.length/3, 3) + " km/h", 100, 30, 10, pr.WHITE)

        pr.end_mode_2d()
        pr.end_drawing()
    
    # Close the window
    pr.unload_texture(squid.body_texture)
    pr.unload_texture(squid.tentacle_texture)
    pr.close_window()

if __name__ == "__main__":
    main()
