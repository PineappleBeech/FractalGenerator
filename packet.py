import io
import socket
import struct
import time


class Packet:
    def __init__(self, *args, from_bytes=False, context=None, sender=None):
        if from_bytes:
            self.context = context
            self.sender = sender
            self.read(args[0])
        else:
            self.args = args

    def write(self, f):
        pass

    def read(self, f):
        pass

    def wait_for_more(self, f, size):
        while len(f.peek(size)) < size:
            pass

    def write_long(self, f, value):
        f.write(struct.pack("!l", value))

    def write_double(self, f, value):
        f.write(struct.pack("!d", value))

    def write_bool(self, f, value):
        f.write(struct.pack("!?", value))

    def write_string(self, f, value):
        data = value.encode("utf-8")
        f.write(struct.pack("!l", len(data)))
        f.write(data)

    def write_id(self, f):
        self.write_long(f, packets.index(type(self)))

    def read_long(self, f):
        self.wait_for_more(f, 4)
        return struct.unpack("!l", f.read(4))[0]

    def read_double(self, f):
        self.wait_for_more(f, 8)
        return struct.unpack("!d", f.read(8))[0]

    def read_bool(self, f):
        self.wait_for_more(f, 1)
        return struct.unpack("!?", f.read(1))[0]

    def read_string(self, f):
        self.wait_for_more(f, 4)
        length = struct.unpack("!l", f.read(4))[0]
        self.wait_for_more(f, length)
        return str(f.read(length), encoding="utf-8")


class TestPacket(Packet):
    def write(self, f):
        self.write_id(f)
        self.write_double(f, time.time())
        self.write_string(f, self.args[0])


    def read(self, f):
        l = self.read_double(f)
        s = self.read_string(f)
        print(l)
        print(s)
        print(self.context)


class ConnectC2SPacket(Packet):
    def write(self, f):
        self.write_id(f)

        name = self.args[0]

        self.write_string(f, name)

    def read(self, f):
        name = self.read_string(f)
        self.context.on_connect(name, self.sender)


class ConnectS2CPacket(Packet):
    def write(self, f):
        self.write_id(f)

        id = self.args[0]

        self.write_string(f, id)

    def read(self, f):
        id = self.read_string(f)
        self.context.multiplayer_id = id
        self.context.tick_multiplayer_checklist("id")


class UpdateShapeS2CPacket(Packet):
    def write(self, f):
        self.write_id(f)

        shape = self.args[0]

        self.write_string(f, shape)

    def read(self, f):
        shape = self.read_string(f)
        self.context.set_shape(shape)
        self.context.tick_multiplayer_checklist("shape")


class UpdateStepS2CPacket(Packet):
    def write(self, f):
        self.write_id(f)

        step = self.args[0]

        self.write_long(f, step)

    def read(self, f):
        step = self.read_long(f)
        self.context.set_step(step)
        self.context.tick_multiplayer_checklist("step")


class UpdateTimeS2CPacket(Packet):
    def write(self, f):
        self.write_id(f)

        time = self.args[0]
        reference_time = self.args[1]
        paused = self.args[2]

        self.write_double(f, time)
        self.write_double(f, reference_time)
        self.write_bool(f, paused)

    def read(self, f):
        timer_time = self.read_double(f)
        reference_time = self.read_double(f)
        paused = self.read_bool(f)

        if paused != self.context.root.timer.is_paused:
            self.context.root.timer.toggle_pause()

        time_diff = time.time() - reference_time

        self.context.root.timer.time = timer_time + time_diff

        self.context.tick_multiplayer_checklist("time")


class UpdateAllPositionsS2CPacket(Packet):
    def write(self, f):
        self.write_id(f)

        player_count = len(self.args[0])

        self.write_long(f, player_count)

        for i in self.args[0]:
            self.write_string(f, self.args[0][i].id)

            for j in range(3):
                self.write_double(f, self.args[0][i].pos[j])
            self.write_double(f, self.args[0][i].scale)


    def read(self, f):
        player_count = self.read_long(f)

        players = {}

        for i in range(player_count):
            player_id = self.read_string(f)

            player = {}

            player["position"] = [self.read_double(f),
                                  self.read_double(f),
                                  self.read_double(f)]

            player["scale"] = self.read_double(f)

            players[player_id] = player

        self.context.players = players
        del self.context.players[self.context.multiplayer_id]

        self.context.tick_multiplayer_checklist("players")

        self.context.multiplayer_connection.send_packet(UpdatePositionC2SPacket(self.context.camera.position, self.context.speed_scale))


class UpdatePositionC2SPacket(Packet):
    def write(self, f):
        self.write_id(f)

        position = self.args[0]
        scale = self.args[1]

        for i in range(3):
            self.write_double(f, position[i])

        self.write_double(f, scale)


    def read(self, f):
        position = []

        for i in range(3):
            position.append(self.read_double(f))

        scale = self.read_double(f)

        self.context.players[self.sender].pos = tuple(position)
        self.context.players[self.sender].scale = scale


packets = [TestPacket,
           ConnectC2SPacket,
           ConnectS2CPacket,
           UpdateShapeS2CPacket,
           UpdateStepS2CPacket,
           UpdateTimeS2CPacket,
           UpdateAllPositionsS2CPacket,
           UpdatePositionC2SPacket]


class PacketReader:
    def __init__(self, context):
        self.context = context

    def read_packet(self, f, sender=None):
        while len(f.peek(4)) < 4:
            pass

        id = struct.unpack("!l", f.read(4))[0]
        packets[id](f, from_bytes=True, context=self.context, sender=sender)


