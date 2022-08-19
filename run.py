import time

import moderngl_window as mglw
from pathlib import Path
import moderngl as mgl
import pygame
from moderngl_window import geometry
from moderngl_window.scene.camera import KeyboardCamera
import math
import numpy as np
import io
import string
from enum import Enum

from shape_compiler import ShapeCodeReader
from button import Button, TextBox
from network import ClientConnection
import packet


class Window(mglw.WindowConfig):
    window_size = (1280, 720)
    gl_version = (4, 3)
    resource_dir = (Path(__file__).parent / 'resources').resolve()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        pygame.font.init()
        self.font = pygame.font.SysFont('Comic Sans MS', 30)

        self.current_window_size = self.window_size

        self.frames = {"ingame": InGameFrame(self),
                       "blank": BaseFrame(self),
                       "paused": PausedFrame(self),
                       "intro": IntroFrame(self),
                       "modeselect": ModeSelectFrame(self),
                       "choosename": ChooseNameFrame(self),
                       "loading": LoadingFrame(self)}

        self.current_frame = "intro"
        self.get_frame().switch_to()

    def render(self, time, frametime):
        self.get_frame().render(time, frametime)

    def key_event(self, key, action, modifiers):
        self.get_frame().key_event(key, action, modifiers)

    def mouse_position_event(self, x: int, y: int, dx, dy):
        self.get_frame().mouse_position_event(x, y, dx, dy)

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        self.get_frame().mouse_scroll_event(x_offset, y_offset)

    def mouse_press_event(self, x: int, y: int, button: int):
        self.get_frame().mouse_press_event(x, y, button)

    def resize(self, width: int, height: int):
        self.current_window_size = (width, height)
        for frame in self.frames:
            self.frames[frame].resize(width, height)

    def make_and_load_compute_shader(self):
        shader: str = self.load_text("main.glsl")
        code: str = self.load_text("shape.txt")

        code_reader = ShapeCodeReader(self.step)
        converted_code = code_reader.compile_code(code)

        shader = shader.replace("//PutDEHere", converted_code)

        #print(converted_code)
        self.compute = self.ctx.compute_shader(shader)

    def make_texture(self, x, y):
        texture = self.ctx.texture((x, y), 4)
        texture.filter = mgl.NEAREST, mgl.NEAREST
        return texture

    def get_frame(self):
        return self.frames[self.current_frame]

    def set_frame(self, frame):
        self.get_frame().switch_from()
        self.current_frame = frame
        self.get_frame().switch_to()


class BaseFrame:
    def __init__(self, window):
        self.root = window
        self.wnd = self.root.wnd
        self.ctx = self.root.ctx
        self.font = self.root.font

        self.quad_program = self.root.load_program(vertex_shader="quad_mirror.vsh", fragment_shader="quad.fsh")
        self.quad_fs = geometry.quad_fs()

        self.pg_screen = pygame.Surface(self.root.current_window_size, flags=pygame.SRCALPHA)
        self.pg_texture = self.make_texture(*self.root.window_size)

    def render(self, time, frametime):
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)

        self.pg_screen.fill((0, 0, 0, 0))
        self.draw_pygame()

        texture_data = self.pg_screen.get_view("1")

        self.pg_texture.write(texture_data)

        self.pg_texture.use(location=0)

        self.quad_fs.render(self.quad_program)

    def draw_pygame(self):
        self.draw_text("Blank")

    def draw_text(self, text, pos=(0, 0), colour=(255, 255, 255)):
        text = self.font.render(text, False, colour)
        self.pg_screen.blit(text, pos)

    def key_event(self, key, action, modifiers):
        pass

    def mouse_position_event(self, x: int, y: int, dx, dy):
        pass

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        pass

    def mouse_press_event(self, x: int, y: int, button: int):
        pass

    def resize(self, width: int, height: int):
        self.pg_texture = self.make_texture(width, height)
        self.pg_screen = pygame.Surface(self.root.current_window_size, flags=pygame.SRCALPHA)

    def switch_to(self):
        pass

    def switch_from(self):
        pass

    def make_texture(self, x, y):
        texture = self.ctx.texture((x, y), 4)
        texture.filter = mgl.NEAREST, mgl.NEAREST
        return texture

class InGameFrame(BaseFrame):
    def __init__(self, window):
        self.root = window
        self.wnd = self.root.wnd
        self.ctx = self.root.ctx
        self.font = self.root.font

        self.multiplayer = False
        self.multiplayer_connection = None
        self.multiplayer_id = None
        self.shape = None
        self.players = None
        self.multiplayer_checklist = {"id": False, "shape": False, "step": False, "time": False, "players": False}

        self.camera = KeyboardCamera(self.wnd.keys, aspect_ratio=self.wnd.aspect_ratio)
        self.camera_enabled = True
        self.camera.set_position(0, 0, 5)
        self.speed_scale = 1

        self.step = 0
        self.make_and_load_compute_shader()
        self.compute['destTex'] = 0
        self.shape_changed = False

        self.quad_program = self.root.load_program(vertex_shader="quad.vsh", fragment_shader="combine_layers.fsh")

        self.current_window_size = self.root.window_size
        self.texture = self.make_texture(*self.root.window_size)
        self.quad_fs = geometry.quad_fs()

        self.pg_screen = pygame.Surface(self.current_window_size, flags=pygame.SRCALPHA)
        self.pg_texture = self.make_texture(*self.root.window_size)

    def render(self, time, frametime):
        if self.shape_changed:
            self.make_and_load_compute_shader()
            self.shape_changed = False

        _ = self.camera.matrix
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)

        w, h = self.texture.size
        gw, gh = 16, 16
        nx, ny, nz = int(w / gw), int(h / gh), 1
        #nx, ny, nz = w, h, 1

        try:
            self.compute['time'] = time
        except Exception:
            pass

        try:
            self.compute['speedScale'] = self.speed_scale
        except Exception:
            pass

        try:
            self.compute["windowSize"] = self.current_window_size
        except KeyError:
            pass

        try:
            #self.compute["cameraMatrix"].write(self.camera.matrix)
            #matrix = tuple(self.camera.matrix)
            #self.compute["cameraMatrix"] = (*tuple(matrix[0]), *tuple(matrix[1]), *tuple(matrix[2]), *tuple(matrix[3]))
            self.compute["cameraMatrix"] = gen_camera_matrix_tuple(self.camera.yaw, self.camera.pitch)
        except KeyError:
            pass

        try:
            self.compute["cameraPos"] = tuple(self.camera.position)
        except KeyError:
            pass

        if self.multiplayer:
            for i, player in enumerate(self.players):
                try:
                    self.compute[f"players[{i}].pos"] = tuple(self.players[player]["position"])
                except KeyError:
                    pass

                try:
                    self.compute[f"players[{i}].scale"] = self.players[player]["scale"] / 10
                except KeyError:
                    pass

        try:
            self.quad_program["texture0"] = 0
        except KeyError:
            pass

        try:
            self.quad_program["texture1"] = 1
        except KeyError:
            pass

        self.texture.bind_to_image(0, read=False, write=True)
        self.compute.run(nx, ny, nz)

        self.texture.use(location=0)

        self.pg_screen.fill((0, 0, 0, 0))
        self.draw_pygame()
        #self.pg_screen.fill((0, 255, 0, 127))
        texture_data = self.pg_screen.get_view("1")

        self.pg_texture.write(texture_data)

        self.pg_texture.use(location=1)

        self.quad_fs.render(self.quad_program)
        #print(self.camera.yaw, self.camera.pitch, tuple(self.camera.position))

    def draw_pygame(self):
        self.draw_text(str(self.step))

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if self.camera_enabled and key != keys.E and key != keys.Q:
            self.camera.key_input(key, action, modifiers)

        if action == keys.ACTION_PRESS:
            if key == keys.C:
                self.camera_enabled = not self.camera_enabled
                self.wnd.mouse_exclusivity = self.camera_enabled
                self.wnd.cursor = not self.camera_enabled

            if key == keys.SPACE and not self.multiplayer:
                self.root.timer.toggle_pause()

            if key == keys.R:
                self.make_and_load_compute_shader()

            if key == keys.RIGHT and not self.multiplayer:
                self.step += 1
                self.make_and_load_compute_shader()
                print(self.step)
            if key == keys.LEFT and not self.multiplayer:
                self.step -= 1
                self.make_and_load_compute_shader()
                print(self.step)

            if key == keys.E:
                self.root.set_frame("paused")

    def mouse_position_event(self, x: int, y: int, dx, dy):
        if self.camera_enabled:
            self.camera.rot_state(-dx, -dy)

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        self.speed_scale = self.speed_scale * (1.1 ** y_offset)
        self.camera.velocity = self.speed_scale * 5.0

    def resize(self, width: int, height: int):
        self.current_window_size = (width, height)
        self.texture = self.make_texture(width, height)
        self.pg_texture = self.make_texture(width, height)
        self.pg_screen = pygame.Surface(self.root.current_window_size, flags=pygame.SRCALPHA)

    def switch_to(self):
        self.wnd.mouse_exclusivity = self.camera_enabled
        self.wnd.cursor = not self.camera_enabled
        try:
            self.root.timer.start()
        except TypeError:
            pass

    def switch_from(self):
        self.wnd.mouse_exclusivity = False
        self.wnd.cursor = True
        self.root.timer.pause()

    def make_and_load_compute_shader(self):
        shader: str = self.root.load_text("main.glsl")
        if self.multiplayer:
            code = self.shape
        else:
            code = self.root.load_text("shape.txt")

        code_reader = ShapeCodeReader(self.step, multiplayer=self.multiplayer)
        converted_code = code_reader.compile_code(code)

        shader = shader.replace("//PutDEHere", converted_code)

        #print(converted_code)
        self.compute = self.ctx.compute_shader(shader)

    def reset_multiplayer_checklist(self):
        for i in self.multiplayer_checklist:
            self.multiplayer_checklist[i] = False

    def check_multiplayer_checklist(self):
        for i in self.multiplayer_checklist:
            if not self.multiplayer_checklist[i]:
                return False
        self.root.set_frame("ingame")

    def tick_multiplayer_checklist(self, item):
        if not self.multiplayer_checklist[item]:
            self.multiplayer_checklist[item] = True
            self.check_multiplayer_checklist()

    def set_shape(self, shape):
        self.shape = shape
        self.shape_changed = True

    def set_step(self, step):
        self.step = step
        self.shape_changed = True


class PausedFrame(BaseFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.return_button = Button("Back", lambda: self.root.set_frame("ingame"), (100, 100), self.font)

    def draw_pygame(self):
        self.pg_screen.fill("grey")
        self.draw_text("Paused")
        self.return_button.draw(self.pg_screen)

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if action == keys.ACTION_PRESS:
            if key == keys.E:
                self.root.set_frame("ingame")

    def mouse_press_event(self, x: int, y: int, button: int):
        if button == 1:
            self.return_button.on_click(x, y)


class IntroFrame(BaseFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.continue_button = Button("Continue", lambda: self.root.set_frame("modeselect"), (100, 400), self.font)

    def draw_pygame(self):
        self.pg_screen.fill("grey")
        self.draw_text("Welcome", (100, 100))
        self.draw_text("WASD to move", (100, 140))
        self.draw_text("E to pause", (100, 180))
        self.draw_text("R to reload shaders", (100, 220))
        self.draw_text("Space to pause and play the timer", (100, 260))
        self.draw_text("ESC to quit", (100, 300))
        self.draw_text("Left and Right Arrow to change the step", (100, 340))

        self.continue_button.draw(self.pg_screen)

    def mouse_press_event(self, x: int, y: int, button: int):
        if button == 1:
            self.continue_button.on_click(x, y)


class ModeSelectFrame(BaseFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.singleplayer_button = Button("Singleplayer", self.select_singleplayer, (100, 300), self.font)
        self.multiplayer_button = Button("Multiplayer", self.select_multiplayer, (100, 400), self.font)

    def draw_pygame(self):
        self.pg_screen.fill("grey")
        self.draw_text("Choose a gamemode", (100, 100))

        self.singleplayer_button.draw(self.pg_screen)
        self.multiplayer_button.draw(self.pg_screen)

    def mouse_press_event(self, x: int, y: int, button: int):
        if button == 1:
            self.singleplayer_button.on_click(x, y)
            self.multiplayer_button.on_click(x, y)

    def select_singleplayer(self):
        self.root.set_frame("ingame")

    def select_multiplayer(self):
        self.root.set_frame("choosename")


class ChooseNameFrame(BaseFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.continue_button = Button("Continue", self.press_continue_button, (100, 400), self.font)
        self.name_box = TextBox((100, 300), self.font)

    def draw_pygame(self):
        self.pg_screen.fill("grey")
        self.draw_text("Enter a name", (100, 100))

        self.continue_button.draw(self.pg_screen)
        self.name_box.draw(self.pg_screen)

    def mouse_press_event(self, x: int, y: int, button: int):
        if button == 1:
            self.continue_button.on_click(x, y)
            self.name_box.on_click(x, y)

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if action == keys.ACTION_PRESS:
            self.name_box.on_key(key, keys)

    def press_continue_button(self):
        self.root.set_frame("loading")
        ingame_frame = self.root.frames["ingame"]
        ingame_frame.multiplayer = True
        ingame_frame.reset_multiplayer_checklist()
        ingame_frame.multiplayer_connection = ClientConnection(ingame_frame)
        ingame_frame.multiplayer_connection.send_packet(packet.ConnectC2SPacket(self.name_box.text))


class LoadingFrame(BaseFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draw_pygame(self):
        self.pg_screen.fill("grey")
        self.draw_text("Loading", (100, 100))


def gen_camera_matrix_tuple(yaw2, pitch2):
    yaw = (yaw2 + 90) / 180 * math.pi # starts at -90 degrees
    pitch = pitch2 / 180 * math.pi

    yaw_matrix = np.array([[math.cos(yaw), 0, math.sin(yaw)],
                           [0, 1, 0],
                           [-math.sin(yaw), 0, math.cos(yaw)]])

    pitch_matrix = np.array([[1, 0, 0],
                             [0, math.cos(pitch), math.sin(pitch)],
                             [0, -math.sin(pitch), math.cos(pitch)]])

    #matrix = np.matmul(yaw_matrix, pitch_matrix)
    matrix = np.matmul(pitch_matrix, yaw_matrix)
    return tuple(matrix.reshape((-1)))


if __name__ == '__main__':
    mglw.run_window_config(Window, args=('--window', 'pygame2'))
