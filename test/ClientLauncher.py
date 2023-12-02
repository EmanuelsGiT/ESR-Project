import sys
import socket
from tkinter import Tk
from Client import Client
from OlyPacket import OlyPacket

from PyQt5.QtWidgets import QApplication

OLY_BUFFER_SIZE = 250
OLY_PORT = 5555

class ClientLauncher:

    HELLO = "HELLO"
    HELLORESPONSE = "HELLORESPONSE"

    def __init__(self,bootstrapperAdressPort):
        self.bootstrapperAdressPort = bootstrapperAdressPort
        self.neighbour = ""
        

    def send_hello_packet(self):
        HelloPacket = OlyPacket()
        HelloPacket = HelloPacket.encode(self.HELLO,[])

        # Cliente envia mensagem de Hello ao bootstrapper para saber a quem se ligar
        self.UDPClientSocket.sendto(HelloPacket,self.bootstrapperAdressPort)

    def receive_hello_packet(self):
        # Recebe respostas do bootstrapper

        bytesAddressPair = self.UDPServerSocket.recvfrom(OLY_BUFFER_SIZE)
        msg = bytesAddressPair[0]

        HelloPacket = OlyPacket()
        HelloPacket = HelloPacket.decode(msg)

        # Pacote Hello Response
        if HelloPacket.type==self.HELLORESPONSE:
            print("Vizinhos: ", end ="")
            print(HelloPacket.payload)
            # O payload é os vizinhos do nodo
            data = HelloPacket.payload
            neighbours = data[:-2]
            self.neighbour = neighbours[0]

    def launch_client(self):
        app = QApplication(sys.argv)# ????
        client = Client(self.neighbour,self.UDPServerSocket)
        client.resize(400, 300)
        client.show()
        sys.exit(app.exec_())
        
    def run(self):
        print("-----------CLIENT------------")
        # Cliente envia mensagem de Hello ao bootstrapper para saber a quem se ligar
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind(('',OLY_PORT))

        self.send_hello_packet()
        self.receive_hello_packet()

        self.launch_client()