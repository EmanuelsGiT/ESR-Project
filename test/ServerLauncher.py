import sys, socket
from datetime import datetime

import time
from threading import Thread
from OlyPacket import OlyPacket
from ServerWorker import ServerWorker
from Bootstrapper import Bootstrapper

OLY_BUFFER_SIZE = 250
OLY_PORT = 5555

PERIODIC_MONITORIZATION_TIME = 5 #segundos

class ServerLauncher:

    PROBE = "PROBE"
    HELLO = "HELLO"
    HELLORESPONSE = "HELLORESPONSE"

    def __init__(self, bootstrapperAddressPort, filename):
        self.bootstrapperAddressPort = bootstrapperAddressPort
        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind(('',OLY_PORT))
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.filename = filename
        self.rp = ""
        self.ip = ""

    def send_hello_packet(self):
        HelloPacket = OlyPacket()
        HelloPacket = HelloPacket.encode(self.HELLO,[])
        self.UDPClientSocket.sendto(HelloPacket,self.bootstrapperAddressPort)

    def send_probe_packet(self):
        while True:
            # Cria mensagem de proba
            ProbePacket = OlyPacket()
            timestamp = datetime.now().strftime('%H:%M:%S.%f')
            data = [timestamp,self.ip]
            ProbePacket = ProbePacket.encode(self.PROBE,data)
            print("Mensagem de proba enviada")

            # Envia mensagem de proba para o vizinho (o servidor só tem um vizinho)
            self.UDPClientSocket.sendto(ProbePacket,(self.rp,OLY_PORT))
            time.sleep(PERIODIC_MONITORIZATION_TIME)
    
    def receive_hello_packet(self):
        bytesAddressPair = self.UDPServerSocket.recvfrom(OLY_BUFFER_SIZE)
        msg = bytesAddressPair[0]
        HRPacket = OlyPacket()
        HRPacket = HRPacket.decode(msg)
        if HRPacket.type == self.HELLORESPONSE:
            # Recebe RP do bootstrapper
            data = HRPacket.payload
            neighbours = data[:-1]
            self.rp = neighbours[-1]
            self.ip = data[-2]

            print("RP: " + self.rp)
        else:
            print("ERROR")

    def run(self):
        # O nodo tem que mandar uma menssagem de registo
        self.send_hello_packet()
        self.receive_hello_packet()

        #Monitorização periódica
        Thread(target=self.send_probe_packet).start() 

        #Start Server Worker
        ServerWorker(self.rp, self.filename, self.UDPServerSocket).run()