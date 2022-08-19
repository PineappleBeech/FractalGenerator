import socket
import threading
import packet
import uuid

server_address = ("www.pineapplebeech.co.uk", 35753)
server_socket = 25565


class ClientConnection:
    def __init__(self, window):
        self.window = window
        self.packet_reader = packet.PacketReader(window)
        self.sending_lock = threading.Lock()

        self.connect()

        self.thread = threading.Thread(target=self.main_loop, daemon=True)
        self.thread.start()

    def main_loop(self):
        while True:
            self.packet_reader.read_packet(self.socket_read_file)

    def send_packet(self, packet):
        self.ensure_connected()

        self.sending_lock.acquire()
        with self.socket.makefile(mode="wb") as s:
            packet.write(s)

        self.sending_lock.release()


    def connect(self):
        self.socket = socket.socket()
        self.socket.connect(server_address)
        self.socket_read_file = self.socket.makefile(mode="rb")

    def ensure_connected(self):
        try:
            self.socket
        except AttributeError:
            self.connect()

class ServerConnection:
    def __init__(self, world):
        self.world = world
        self.packet_reader = packet.PacketReader(world)
        self.threads = {}
        self.connections = {}
        self.sending_lock = threading.Lock()

        self.make_server_socket()

        self.thread = threading.Thread(target=self.main_loop)
        self.thread.start()

    def main_loop(self):
        #self.socket_read_file = self.socket.makefile(mode="r")

        while True:
            conn, _ = self.socket.accept()
            conn_uuid = str(uuid.uuid4())
            thread = threading.Thread(target=self.connection_loop(conn, conn_uuid))

            self.threads[conn_uuid] = thread
            self.connections[conn_uuid] = conn

            thread.start()


    def make_server_socket(self):
        self.socket = socket.socket()
        self.socket.bind(("", server_socket))
        self.socket.listen(5)

    def connection_loop(self, conn, conn_id):
        def func():
            socket_read_file = conn.makefile(mode="rb")
            try:
                while True:
                    self.packet_reader.read_packet(socket_read_file, sender=conn_id)
            except ConnectionResetError as e:
                del self.connections[conn_id]
                del self.threads[conn_id]
                self.world.on_disconnect(conn_id)
                print(conn_id, "has disconnected")

        return func

    def send_packet(self, packet, conn_id):

        self.sending_lock.acquire()
        with self.connections[conn_id].makefile(mode="wb") as s:
            packet.write(s)

        self.sending_lock.release()

    def send_packet_to_all(self, packet):
        for conn_id in self.connections:
            self.send_packet(packet, conn_id)