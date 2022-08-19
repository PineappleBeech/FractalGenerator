import network
import packet
import time
import threading


class Timer:
    def __init__(self):
        self.time_internal = 0.0
        self.reference_time = time.time()
        self.paused = False

    def get_time(self):
        if self.paused:
            return self.time_internal
        else:
            current_time = time.time()
            self.time_internal += current_time - self.reference_time
            self.reference_time = current_time
            return self.time_internal

    def toggle_pause(self):
        if self.paused:
            self.reference_time = time.time()
            self.paused = False

        else:
            self.paused = True

            current_time = time.time()
            self.time_internal += current_time - self.reference_time
            self.reference_time = current_time


class Player:
    def __init__(self, id, name, server, pos=(0 ,0, 5), rot=(0, -90), scale=1):
        self.id = id
        self.name = name
        self.pos = pos
        self.rot = rot
        self.scale = scale
        self.server = server

    def send_packet(self, packet):
        self.server.connection.send_packet(packet, self.id)

class Server:
    def __init__(self):
        self.tick_rate = 20
        self.tick_time = 1.0/self.tick_rate
        self.players = {}
        self.shape = self.load_shape_file()
        self.step = 3
        self.timer = Timer()

        self.connection = network.ServerConnection(self)

        self.thread = threading.Thread(target=self.main_loop, daemon=True)

    def run(self):
        self.thread.start()

        while True:
            self.process_command(input("> "))

    def main_loop(self):
        while True:
            tick_start_time = time.time()
            self.send_to_all(packet.UpdateAllPositionsS2CPacket(self.players))

            while time.time() < tick_start_time + self.tick_time:
                pass


    def on_connect(self, name, id):
        print(f"{name} has connected")
        player = Player(id, name, self)
        self.players[id] = player

        player.send_packet(packet.ConnectS2CPacket(id))
        player.send_packet(packet.UpdateShapeS2CPacket(self.shape))
        player.send_packet(packet.UpdateStepS2CPacket(self.step))
        player.send_packet(packet.UpdateTimeS2CPacket(self.timer.get_time(), time.time(), self.timer.paused))
        player.send_packet(packet.UpdateAllPositionsS2CPacket(self.players))

    def on_disconnect(self, id):
        del self.players[id]

    def load_shape_file(self):
        with open("resources/server_shape.txt") as f:
            return f.read()

    def send_to_all(self, packet):
        for i in self.players:
            self.players[i].send_packet(packet)

    def get_player_by_name(self, name):
        for i in self.players:
            if self.players[i].name == name:
                return self.players[i]

    def process_command(self, command):
        args = command.split()
        if args[0] == "pause":
            self.timer.toggle_pause()
            self.send_to_all(packet.UpdateTimeS2CPacket(self.timer.get_time(), time.time(), self.timer.paused))

        elif args[0] == "reload":
            self.shape = self.load_shape_file()
            self.send_to_all(packet.UpdateShapeS2CPacket(self.shape))

        elif args[0] == "step":
            self.step = int(args[1])
            self.send_to_all(packet.UpdateStepS2CPacket(self.step))

        elif args[0] == "tp":
            player1 = self.get_player_by_name(args[1])
            player2 = self.get_player_by_name(args[2])
            player1.pos = player2.pos
            player1.scale = player2.scale



if __name__ == '__main__':
    server = Server()
    server.run()