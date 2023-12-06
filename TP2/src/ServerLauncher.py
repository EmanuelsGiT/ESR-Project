import sys, socket
from datetime import datetime

import time
from threading import Thread
from RtspPacket import RtspPacket
from ServerWorker import ServerWorker
from Bootstrapper import Bootstrapper

RTSP_BUFFER_SIZE = 250
RTSP_PORT = 5555
RTP_PORT = 6666

PERIODIC_MONITORIZATION_TIME = 5 #segundos

class ServerLauncher:

    PROBE = "PROBE"
    HELLO = "HELLO"
    HELLORESPONSE = "HELLORESPONSE"

    def __init__(self, bootstrapperAddress, movies):
        self.bootstrapperAddress = bootstrapperAddress
        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind(('',RTSP_PORT))
        self.UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.movies = movies
        self.sockets = {}
        self.rp = ""
        self.ip = ""

    def send_hello_packet(self):
        HelloPacket = RtspPacket()
        HelloPacket = HelloPacket.encode(self.HELLO,[])
        self.UDPClientSocket.sendto(HelloPacket,self.bootstrapperAddress)

    def send_probe_packet(self):
        while True:
            # Cria mensagem de proba
            ProbePacket = RtspPacket()
            timestamp = datetime.now().strftime('%H:%M:%S.%f')
            data = [timestamp,self.ip]
            ProbePacket = ProbePacket.encode(self.PROBE,data)
            print("Mensagem de proba enviada")

            # Envia mensagem de proba para o rp
            self.UDPClientSocket.sendto(ProbePacket,(self.rp,RTSP_PORT))
            time.sleep(PERIODIC_MONITORIZATION_TIME)
    
    def receive_hello_packet(self):
        bytesAddressPair = self.UDPServerSocket.recvfrom(RTSP_BUFFER_SIZE)
        msg = bytesAddressPair[0]
        HRPacket = RtspPacket()
        HRPacket = HRPacket.decode(msg)
        if HRPacket.type == self.HELLORESPONSE:
            # Recebe RP do bootstrapper
            data = HRPacket.payload
            neighbours = data[:-1]
            self.rp = data[-1]
            self.ip = neighbours[-1]

        else:
            print("ERROR")

    def run(self):
        # O nodo tem que mandar uma menssagem de registo
        self.send_hello_packet()
        self.receive_hello_packet()

        #Monitorização periódica
        Thread(target=self.send_probe_packet).start() 

        #Start Server Workers
        
        RTPPORT = RTP_PORT
        RTSPPORT = RTSP_PORT 
        
        ServerWorker(self.rp, self.movies[0], self.UDPServerSocket, RTPPORT).run()
        
        for i in (1,len(self.movies)-1):
            RTPPORT += 1 
            RTSPPORT += 1

            UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            UDPServerSocket.bind(('',RTSPPORT))

            ServerWorker(self.rp, self.movies[i], UDPServerSocket, RTPPORT).run()



