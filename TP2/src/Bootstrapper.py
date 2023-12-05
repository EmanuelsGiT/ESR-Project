import socket
from RtspPacket import *
from threading import Thread, Lock

# Tabela quem mantém a informção à cerca de toda a topologia da overlay
class OverlayTable:
    @classmethod
    def __init__(self):
        self.groups = []
        self.rp = ""
        self.lock = Lock()

    @classmethod
    def add_group(self,ip,neighbours):
        self.groups.append({ "ip" : ip ,"neighbours" : neighbours })

    def get_neighbours(self,ip):
        self.lock.acquire()
        try:
            neighbours = []
            for group in self.groups:
                if group["ip"] == ip:
                    for neighbour in group["neighbours"]:
                        neighbours.append(neighbour)
            return neighbours
        except Exception as e:
            print(e)
        finally:
            self.lock.release()

    @classmethod
    def load(self,configFile):
        f = open(configFile, "r")

        neighbours = []
        ip = ""
        for line in f:
            line = line.strip()
            if line == "":
                continue
            if line[0] == 'R':
                self.rp = line[3:]
            elif line[0]=='#':
                if neighbours != []:
                    self.add_group(ip,neighbours)
                ip = line[1:]
                neighbours = []
            else:
                neighbours.append(line)

        if neighbours != []:
            self.add_group(ip,neighbours)
        f.close()


    @classmethod
    def display(self):
        for group in  self.groups:
            for neighbour in group["neighbours"]:
                print(neighbour)

class Bootstrapper:

    HELLO = "HELLO"
    HELLORESPONSE = "HELLORESPONSE"

    def __init__(self, configFile):
        self.overlayTable = OverlayTable()
        self.overlayTable.load(configFile)

    def run(self):
        Thread(target=self.service_bootstrapper).start()

    def handler(self, bytesAddressPair):
        ip = bytesAddressPair[1][0]
        msg = bytesAddressPair[0]

        HelloPacket = RtspPacket()
        HelloPacket = HelloPacket.decode(msg)

        if HelloPacket.type==self.HELLO:
            print("Recebi mensagem hello | IP: " + ip)
            # Ir buscar os vizinhos do nodo que se ligou
            neighbours = self.overlayTable.get_neighbours(ip)
            data = neighbours
            data.append(ip)
            data.append(self.overlayTable.rp)

            HelloResponsePack = RtspPacket()
            HelloResponsePack = HelloResponsePack.encode(self.HELLORESPONSE,data)

            self.rtspClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            self.rtspClientSocket.sendto(HelloResponsePack,(ip,RTSP_PORT))

    # Bootstrapper listening
    def service_bootstrapper(self):
       self.rtspServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
       self.rtspServerSocket.bind(('',RTSP_PORT))

       while(True):
           bytesAddressPair = self.rtspServerSocket.recvfrom(RTSP_BUFFER_SIZE)

            # Aqui chamamos um handler para interpretar a msg e agir de acordo
           thread = Thread(target=self.handler,args=[bytesAddressPair])
           thread.start()

       os._exit(0)