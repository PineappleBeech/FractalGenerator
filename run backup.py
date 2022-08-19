import moderngl_window as mglw
from pathlib import Path
import moderngl as mgl
from moderngl_window import geometry
from moderngl_window.scene.camera import KeyboardCamera
import math
import numpy as np
import io
import string
from enum import Enum

from shape_compiler import ShapeCodeReader


class Window(mglw.WindowConfig):
    window_size = (1280, 720)
    gl_version = (4, 3)
    resource_dir = (Path(__file__).parent / 'resources').resolve()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frames = {"ingame": InGameFrame(self)}
        self.current_frame = "ingame"


        self.camera = KeyboardCamera(self.wnd.keys, aspect_ratio=self.wnd.aspect_ratio)
        self.camera_enabled = True
        self.camera.set_position(0, 0, 5)
        self.speed_scale = 1

        self.wnd.mouse_exclusivity = True

        self.step = 0
        self.make_and_load_compute_shader()
        self.compute['destTex'] = 0

        self.quad_program = self.load_program(vertex_shader="quad.vsh", fragment_shader="quad.fsh")

        self.current_window_size = self.window_size
        self.texture = self.make_texture(*self.window_size)
        self.quad_fs = geometry.quad_fs()

    def render(self, time, frametime):
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

        self.texture.bind_to_image(0, read=False, write=True)
        self.compute.run(nx, ny, nz)

        self.texture.use(location=0)
        self.quad_fs.render(self.quad_program)
        #print(self.camera.yaw, self.camera.pitch, tuple(self.camera.position))


    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if self.camera_enabled:
            self.camera.key_input(key, action, modifiers)

        if action == keys.ACTION_PRESS:
            if key == keys.C:
                self.camera_enabled = not self.camera_enabled
                self.wnd.mouse_exclusivity = self.camera_enabled
                self.wnd.cursor = not self.camera_enabled
            if key == keys.SPACE:
                self.timer.toggle_pause()
            if key == keys.R:
                self.make_and_load_compute_shader()

            if key == keys.RIGHT:
                self.step += 1
                self.make_and_load_compute_shader()
                print(self.step)
            if key == keys.LEFT:
                self.step -= 1
                self.make_and_load_compute_shader()
                print(self.step)

    def mouse_position_event(self, x: int, y: int, dx, dy):
        if self.camera_enabled:
            self.camera.rot_state(-dx, -dy)

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        self.speed_scale = self.speed_scale * (1.1 ** y_offset)
        self.camera.velocity = self.speed_scale * 5.0

    def resize(self, width: int, height: int):
        self.current_window_size = (width, height)
        self.texture = self.make_texture(width, height)

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


class InGameFrame:
    def __init__(self, window):
        self.window = window


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
