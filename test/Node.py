import socket
from threading import Thread, Lock
import sys
import os
import pickle
import random
from datetime import datetime, date, timedelta
from OlyPacket import *
from StreamTables import *
from RtpPacket import RtpPacket

RTP_BUFFER_SIZE = 20480
RTP_PORT = 9999
MAX_DELTA = timedelta(days = 1)
MIN_DELTA = timedelta(milliseconds = 200)
ZERO_DELTA = timedelta(microseconds = 1)
VALIDATE_TIME = timedelta(seconds = 10)

class Route:
    def __init__(self,source,saltos,delta, time):
        self.source = source
        self.saltos = saltos
        self.delta = delta
        self.time = datetime.combine(date.today(), time)

    def update_route(self,source,saltos,delta, time):
        difSaltos = self.saltos - saltos
        difTime = time - self.time
        difDelta = delta - self.delta
        #Dá update à rota se:
            #O tempo de validade tiver expirado, ou
            #Houver redução de saltos e tiver melhora de tempo, ou
            #Tiver melhora de tempo significativa (MIN_DELTA)
        if(difTime >= VALIDATE_TIME or (difDelta >= ZERO_DELTA and difSaltos > 0) or difDelta > MIN_DELTA): #Ou recebe uma rota melhor ou o rota expirou
            self.delta = delta
            self.source = source
            self.saltos = saltos
            self.time = time
            return True
        return False        

class Node:

    HELLO = "HELLO"
    HELLORESPONSE = "HELLORESPONSE"
    PROBE = "PROBE"
    SETUP = "SETUP"
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    TEARDOWN = "TEARDOWN"

    def __init__(self, bootstrapperAddressPort):
        self.bootstrapperAddressPort = bootstrapperAddressPort
        self.neighbours = []
        self.streamsTable = StreamsTable()
        self.route = Route("",0,MAX_DELTA, datetime.now().time())
        self.lock = Lock()

    def run(self):
        print("--------------Node--------------")
        Thread(target=self.service_RTP).start()
        Thread(target=self.service_OLY).start()

    def OLY_handler(self, bytesAddressPair):
        source = bytesAddressPair[1][0]
        msg = bytesAddressPair[0]

        Packet = OlyPacket()
        Packet = Packet.decode(msg)

        # Pacote Hello Response
        if Packet.type==self.HELLORESPONSE:
            # O payload é os vizinhos do nodo
            print("Vizinhos: ", end ="")
            print(Packet.payload)

            data = Packet.payload
            self.neighbours = data[:-1]
            self.ip = data[-1]

        # Pacote de proba
        elif Packet.type==self.PROBE:
            now = datetime.now()
            now = now.time()
            # Timestamp marcado no servidor
            timestamp = datetime.strptime(Packet.payload[0], '%H:%M:%S.%f').time()
            delta = datetime.combine(date.today(), now) - datetime.combine(date.today(), timestamp)
            # Número de saltos do servidor até o nodo atual
            saltos = int(Packet.payload[1]) + 1

            # IP de quem enviou pacote de probe
            probeSource = Packet.payload[2]

            self.lock.acquire()
            old_source = self.route.source
            updated = self.route.update_route(probeSource, saltos, delta, datetime.combine(date.today(), now))
            new_source = self.route.source
            if(updated):
                print("Updated Route")
                if(old_source != new_source and self.streamsTable.status == "open"): #TODO
                    print("Updated Source")
                    SetupPacket = OlyPacket()
                    SetupPacket = SetupPacket.encode("SETUP", [])
                    self.olyClientSocket.sendto(SetupPacket,(new_source,OLY_PORT))

                    PlayPacket = OlyPacket()
                    PlayPacket = PlayPacket.encode("PLAY", [])
                    self.olyClientSocket.sendto(PlayPacket,(new_source,OLY_PORT))

                    TDNPacket = OlyPacket()
                    TDNPacket = TDNPacket.encode("TEARDOWN", [])
                    self.olyClientSocket.sendto(TDNPacket,(old_source,OLY_PORT))

                # Data a enviar aos nodos viznhos
                data = [timestamp,saltos,self.ip]

                ProbePacket = OlyPacket()
                ProbePacket = ProbePacket.encode("PROBE",data)
                # O nodo envia mensagem de proba a todos os seus vizinhos ativos
                for neighbour in self.neighbours:
                    #print("NodeIP: " + elem + " | SOURCEIP: " + source_ip)
                    if neighbour != probeSource:
                        self.olyClientSocket.sendto(ProbePacket,(neighbour,OLY_PORT))
            self.lock.release()
        else:
            destination = self.route.source

            if Packet.type==self.SETUP:
                print("Criei novo fluxo | destination: " + source)
                self.lock.acquire()
                # Preciso implementar mensagens de proba para conseguirmos saber isto
                # Adicionar um fluxo à routing table falta passar o dest (novo vizinho a qual o novo atual passa stream)
                firstStream = self.streamsTable.is_empty()
                self.streamsTable.add_stream(source) #o destino da stream é a source de quem fez o pedido

                if(firstStream):
                    self.olyClientSocket.sendto(msg,(destination,OLY_PORT))
                    print("sending SETUP to " + destination)
                self.lock.release()

            elif Packet.type == self.PLAY:
                print("Fluxo ativo | destination: " + source)
                self.lock.acquire()
                oldStatus = self.streamsTable.stream_table_status()
                self.streamsTable.open_stream(source)
                newStatus = self.streamsTable.stream_table_status()

                if(oldStatus != newStatus):
                    self.olyClientSocket.sendto(msg,(destination,OLY_PORT))
                    print("sending PLAY to " + destination)
                self.lock.release()

            elif Packet.type == self.PAUSE:
                print("Fluxo pausado | destination: " + source)
                self.lock.acquire()
                # Fecha o fluxo pois o nodo vizinhos(source_ip) não quer stream
                oldStatus = self.streamsTable.stream_table_status()
                self.streamsTable.close_stream(source)
                newStatus = self.streamsTable.stream_table_status()

                if(oldStatus != newStatus):
                    self.olyClientSocket.sendto(msg,(destination,OLY_PORT))
                self.lock.release()

            elif Packet.type == self.TEARDOWN:
                print("Fluxo eliminado da destination: " + source)
                # Passar pacote ao próximo nodo
                self.lock.acquire()

                oldStatus = self.streamsTable.stream_table_status()
                # Remover fluxo da tabela de rotas
                self.streamsTable.delete_stream(source)
                newStatus = self.streamsTable.stream_table_status()

                empty = self.streamsTable.is_empty()

                if(empty):
                    self.olyClientSocket.sendto(msg,(destination,OLY_PORT))
                elif(oldStatus != newStatus):
                    msg = Packet.encode(self.PAUSE,[])
                    self.olyClientSocket.sendto(msg,(destination,OLY_PORT))
                self.lock.release()


    def RTP_handler(self,data):
        openStreams = self.streamsTable.get_streams()

        self.lock.acquire()
        for stream in openStreams:
            #print("Redirecionei pacote de stream " + source_ip + " -> " + stream.source)
            self.rtpClientSocket.sendto(data,(stream.destination,RTP_PORT))
        self.lock.release()


    # Listening for OlyPacket
    def service_OLY(self):
        self.olyServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.olyServerSocket.bind(('',OLY_PORT))

        # O nodo tem que mandar uma menssagem de registo
        HelloPacket = OlyPacket()
        HelloPacket = HelloPacket.encode(self.HELLO,"")

        self.olyClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.olyClientSocket.sendto(HelloPacket, self.bootstrapperAddressPort)

        while(True):
            bytesAddressPair = self.olyServerSocket.recvfrom(OLY_BUFFER_SIZE)

            # Aqui chamamos um handler para interpretar a msg e agir de acordo
            thread = Thread(target=self.OLY_handler,args=[bytesAddressPair])
            thread.start()

        os._exit(0)


    def service_RTP(self):
       self.rtpServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
       self.rtpServerSocket.bind(('',RTP_PORT))

       self.rtpClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

       while(True):
           bytesAddressPair = self.rtpServerSocket.recvfrom(RTP_BUFFER_SIZE)
           data = bytesAddressPair[0]

           thread = Thread(target=self.RTP_handler,args=[data])
           thread.start()
       os._exit(0)
