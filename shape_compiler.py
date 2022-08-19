from enum import Enum
import io
import math
import string

identifier_valid_characters = string.ascii_lowercase + string.digits + "_"

class ReturnType(Enum):
    ANY = 0
    FLOAT = 1
    VEC3 = 2


class Marker(Enum):
    END_OF_FUNC = "end_of_function_marker"
    END_OF_LOOP = "end_of_loop_marker"
    END_OF_IF = "end_of_if_marker"


class ShapeSyntaxException(Exception):
    pass


class ShapeCodeReader:
    def __init__(self, step, multiplayer=False):
        self.functions = {}
        self.variables = {"$step": str(step)}
        self.multiplayer = multiplayer

    def compile_code(self, code):
        code_reader = io.StringIO(code)
        if not self.multiplayer:
            return "float de(vec4 pos) {\n    return " + self.read_command(code_reader, return_type="float") + ";\n}"

        else:
            return r"""
float de(vec4 pos) {
    float min_dist = 1000000000.0;
    for (int i=0; i<PLAYER_COUNT; i++) {
        min_dist = min(min_dist, de_sphere(scale(players[i].scale, translate(players[i].pos, pos))));
    }
    min_dist = min(min_dist, inserthere);
    return min_dist;
}""".replace("inserthere", self.read_command(code_reader, return_type="float"))


    def read_command(self, code_reader: io.StringIO, return_type=ReturnType.VEC3):
        full_command = code_reader.readline()
        if full_command == "\n" or full_command[0] == "#":
            return self.read_command(code_reader, return_type=ReturnType.ANY)

        keyword = full_command.split()[0]
        args = full_command.split()[1:]
        if keyword == "endshape":
            requires(return_type, ReturnType.VEC3)
            return "pos"

        if keyword == "endloop":
            return Marker.END_OF_LOOP.value

        if keyword == "endfunction":
            return Marker.END_OF_FUNC.value

        if keyword == "endif":
            return Marker.END_OF_IF.value

        elif keyword == "cube":
            requires(return_type, ReturnType.FLOAT)
            return "de_cube(" + self.read_command(code_reader) + ")"

        elif keyword == "sphere":
            requires(return_type, ReturnType.FLOAT)
            return "de_sphere(" + self.read_command(code_reader) + ")"

        elif keyword == "mirror":

            requires(return_type, ReturnType.VEC3)

            axes = {i for i in args[0] if i in "xyz"}

            return_value = self.read_command(code_reader)

            if "x" in axes:
                return_value = "mirrorX(" + return_value + ")"

            if "y" in axes:
                return_value = "mirrorY(" + return_value + ")"

            if "z" in axes:
                return_value = "mirrorZ(" + return_value + ")"

            return return_value

        elif keyword == "translate":
            requires(return_type, ReturnType.VEC3)
            return "translate(vec3(" + self.process_arg(args[0]) + ", "\
                   + self.process_arg(args[1]) + ", "\
                   + self.process_arg(args[2]) + "), " + self.read_command(code_reader) + ")"

        elif keyword == "rotate" or keyword == "rotate_rad":
            requires(return_type, ReturnType.VEC3)
            if keyword == "rotate":
                angle = str(self.process_float(args[1]) / 180 * math.pi)
            else:
                angle = self.process_arg(args[1])

            if args[0] == "xy" or args[0] == "yx":
                return "rotateXY(" + angle + ", " + self.read_command(code_reader) + ")"
            if args[0] == "xz" or args[0] == "zx":
                return "rotateXZ(" + angle + ", " + self.read_command(code_reader) + ")"
            if args[0] == "yz" or args[0] == "zy":
                return "rotateYZ(" + angle + ", " + self.read_command(code_reader) + ")"

        elif keyword == "scale":
            requires(return_type, ReturnType.VEC3)
            return "scale(" + args[0] + ", " + self.read_command(code_reader) + ")"

        elif keyword == "menger_fold":
            requires(return_type, ReturnType.VEC3)
            return "mengerFold(" + self.read_command(code_reader) + ")"

        elif keyword == "repeat":
            requires(return_type, ReturnType.VEC3)
            axes = {i for i in args[0] if i in "xyz"}

            return_value = self.read_command(code_reader)

            if "x" in axes:
                return_value = "repeatX(" + args[1] + ", " + return_value + ")"
            if "y" in axes:
                return_value = "repeatY(" + args[1] + ", " + return_value + ")"
            if "z" in axes:
                return_value = "repeatZ(" + args[1] + ", " + return_value + ")"

            return return_value

        elif keyword == "loop":
            code_to_loop = self.read_command(code_reader)
            looped_code = Marker.END_OF_LOOP.value
            if Marker.END_OF_LOOP.value not in code_to_loop:
                raise ShapeSyntaxException("missing end of loop marker")

            for i in range(int(self.process_arg(args[0]))):
                looped_code = looped_code.replace(Marker.END_OF_LOOP.value, code_to_loop)

            return looped_code.replace(Marker.END_OF_LOOP.value, self.read_command(code_reader))

        elif keyword == "union":
            requires(return_type, "float")
            return "min("\
                   + self.read_command(code_reader, return_type=ReturnType.FLOAT) + ", "\
                   + self.read_command(code_reader, return_type=ReturnType.FLOAT) + ")"

        elif keyword == "intersection":
            requires(return_type, "float")
            return "max("\
                   + self.read_command(code_reader, return_type=ReturnType.FLOAT) + ", "\
                   + self.read_command(code_reader, return_type=ReturnType.FLOAT) + ")"

        elif keyword == "expand":
            requires(return_type, "float")
            return "expand(" + args[0] + ", " + self.read_command(code_reader, return_type=ReturnType.FLOAT) + ")"

        elif keyword == "if":
            num1 = self.process_float(args[0])
            num2 = self.process_float(args[2])
            op = args[1]

            if op == "==":
                result = num1 == num2
            elif op == "!=":
                result = num1 != num2
            elif op == "<":
                result = num1 < num2
            elif op == ">":
                result = num1 > num2
            elif op == "<=":
                result = num1 <= num2
            elif op == ">=":
                result = num1 >= num2
            else:
                raise ShapeSyntaxException("invalid operation: " + op)

            conditional_code = self.read_command(code_reader, return_type=ReturnType.ANY)

            if Marker.END_OF_IF.value not in conditional_code:
                raise ShapeSyntaxException("missing endif")

            if result:
                return conditional_code.replace(Marker.END_OF_IF.value, self.read_command(code_reader, return_type=ReturnType.ANY))
            else:
                return self.read_command(code_reader, return_type=ReturnType.ANY)

        elif keyword == "set":
            if args[0][0] != "$":
                raise ShapeSyntaxException("variable names must start with a $")
            if any(i not in identifier_valid_characters for i in args[0][1:]):
                raise ShapeSyntaxException("variable names must only include lower case letters, digits and underscoes")

            self.variables[args[0]] = " ".join([self.process_arg(i) for i in args[1:]])
            return self.read_command(code_reader, return_type=return_type)

        elif keyword == "function":
            if any(i not in identifier_valid_characters for i in args[0]):
                raise ShapeSyntaxException("incompatible function name: " + keyword)

            self.functions[args[0]] = self.read_command(code_reader, return_type=ReturnType.ANY)
            return self.read_command(code_reader, return_type=return_type)

        elif keyword in self.functions:
            return self.functions[keyword].replace(Marker.END_OF_FUNC.value, self.read_command(code_reader, ReturnType.ANY))

        else:
            raise ShapeSyntaxException("incorrect command: " + keyword)

    def process_arg(self, arg):
        if arg[0] == "$":
            try:
                return self.variables[arg]
            except KeyError:
                raise ShapeSyntaxException("missing variable name: " + arg[0])

        return arg

    def process_float(self, f):
        return float(self.process_arg(f))

def requires(a, b):
    if a == b:
        return
    if a == ReturnType.ANY:
        return
    else:
        raise ShapeSyntaxException("needed " + a.name + ", got " + b.name)
