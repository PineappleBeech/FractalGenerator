import packet
import io
import network
import time

def main():
    server = network.ServerConnection("server")
    client = network.ClientConnection("client")
    client2 = network.ClientConnection("client")


    client.send_packet(packet.TimePacket("hello"))

    time.sleep(1)

    server.send_packet_to_all(packet.TimePacket("hello back"))

if __name__ == '__main__':
    main()