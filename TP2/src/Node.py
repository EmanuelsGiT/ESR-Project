import socket
from threading import Thread, Lock
import sys
import os
import pickle
import random
from datetime import datetime, date, timedelta
from RtspPacket import *
from StreamTables import *
from RtpPacket import RtpPacket

RTP_BUFFER_SIZE = 20480
RTSP_PORT = 5555
RTP_PORT = 6666
MAX_DELTA = timedelta(days=1)
MIN_DELTA = timedelta(milliseconds=200)
ZERO_DELTA = timedelta(microseconds=1)
VALIDATE_TIME = timedelta(seconds=10)


class Route:
    def __init__(self, source, delta, time):
        self.source = source
        self.delta = delta
        self.time = datetime.combine(date.today(), time)

    def update_route(self, source, delta, time):
        difTime = time - self.time
        difDelta = delta - self.delta
        # Dá update à rota se:
        # O tempo de validade tiver expirado, ou
        # Tiver melhora de tempo significativa (MIN_DELTA)
        if (
            difTime >= VALIDATE_TIME or difDelta > MIN_DELTA
        ):  # Ou recebe uma rota melhor ou o rota expirou
            self.delta = delta
            self.source = source
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

    def __init__(self, bootstrapperAddress, isRp, nmovies):
        self.bootstrapperAddress = bootstrapperAddress
        self.rp = ""
        self.isRp = isRp
        self.nmovies = nmovies
        self.socketsRTSP = {}
        self.socketsRTP = {}
        self.streamsTable = {}
        self.neighbours = []
        self.lock = Lock()

    def run(self):  
        if self.isRp:
            print("---------------RP---------------")
            self.route = Route("", MAX_DELTA, datetime.now().time())
        else:
            print("--------------Node--------------")
        
        RTPPORT = RTP_PORT
        RTSPPORT = RTSP_PORT

        for i in range(0,int(self.nmovies)):
            Thread(target=self.service_RTSP, args=(RTSPPORT,)).start()
            Thread(target=self.service_RTP, args=((RTPPORT,RTSPPORT),)).start()
            RTSPPORT+=1
            RTPPORT+=1


    def RTSP_handler(self, bytesAddressPair, RTSPPORT):
        source = bytesAddressPair[1][0]
        msg = bytesAddressPair[0]

        Packet = RtspPacket()
        Packet = Packet.decode(msg)

        # Pacote Hello Response
        if Packet.type == self.HELLORESPONSE:
            # O payload é os vizinhos do nodo
            print("Vizinhos: ", end="")
            print(Packet.payload)

            data = Packet.payload
            self.rp = data[-1]
            self.neighbours = data[:-1]
            self.ip = data[-2]
        # Pacote de proba
        elif Packet.type == self.PROBE:
            now = datetime.now()
            now = now.time()
            # Timestamp marcado no servidor
            timestamp = datetime.strptime(Packet.payload[0], "%H:%M:%S.%f").time()
            delta = datetime.combine(date.today(), now) - datetime.combine(
                date.today(), timestamp
            )

            # IP de quem enviou pacote de probe
            probeSource = Packet.payload[1]

            self.lock.acquire()
            old_source = self.route.source
            updated = self.route.update_route(
                probeSource, delta, datetime.combine(date.today(), now)
            )
            new_source = self.route.source
            if updated:
                print("Updated Route")
                if (
                    old_source != new_source and self.streamsTable[RTSPPORT].status == "open"
                ):  
                    print("Updated Source")
                    SetupPacket = RtspPacket()
                    SetupPacket = SetupPacket.encode("SETUP", [])
                    self.rtspClientSocket.sendto(SetupPacket, (new_source, RTSPPORT))

                    PlayPacket = RtspPacket()
                    PlayPacket = PlayPacket.encode("PLAY", [])
                    self.rtspClientSocket.sendto(PlayPacket, (new_source, RTSPPORT))

                    TDNPacket = RtspPacket()
                    TDNPacket = TDNPacket.encode("TEARDOWN", [])
                    self.rtspClientSocket.sendto(TDNPacket, (old_source, RTSPPORT))

            self.lock.release()
        else:
            if self.isRp:
                destination = self.route.source
            else:
                destination = self.neighbours[0]

            data = Packet.payload
            port = data[0]
            route = data[1:]
            route.append(self.ip)

            rtsp = RtspPacket()
            new_data = data
            if not self.isRp:
                new_data.append(self.ip)

            if Packet.type == self.SETUP:
                print("Criei novo fluxo | destination: " + source)
                self.lock.acquire()
                # Preciso implementar mensagens de proba para conseguirmos saber isto
                # Adicionar um fluxo à routing table falta passar o dest (novo vizinho a qual o novo atual passa stream)
                firstStream = self.streamsTable[RTSPPORT].is_empty()
                self.streamsTable[RTSPPORT].add_stream(port, route[0], route)  # o destino da stream é a source de quem fez o pedido

                if firstStream:
                    rtsp = rtsp.encode(Packet.type, new_data)
                    self.rtspClientSocket.sendto(rtsp, (destination, RTSPPORT))
                    print("sending SETUP to " + destination)
                self.lock.release()

            elif Packet.type == self.PLAY:
                print("Fluxo ativo | destination: " + source)
                self.lock.acquire()
                oldStatus = self.streamsTable[RTSPPORT].stream_table_status()
                self.streamsTable[RTSPPORT].open_stream(route[0])
                newStatus = self.streamsTable[RTSPPORT].stream_table_status()

                if oldStatus != newStatus:
                    rtsp = rtsp.encode(Packet.type, new_data)
                    self.rtspClientSocket.sendto(rtsp, (destination, RTSPPORT))
                    print("sending PLAY to " + destination)
                self.lock.release()

            elif Packet.type == self.PAUSE:
                print("Fluxo pausado | destination: " + source)
                self.lock.acquire()
                # Fecha o fluxo pois o nodo vizinhos(source_ip) não quer stream
                oldStatus = self.streamsTable[RTSPPORT].stream_table_status()
                self.streamsTable[RTSPPORT].close_stream(route[0])
                newStatus = self.streamsTable[RTSPPORT].stream_table_status()

                if oldStatus != newStatus:
                    rtsp = rtsp.encode(Packet.type, new_data)
                    self.rtspClientSocket.sendto(rtsp, (destination, RTSPPORT))
                self.lock.release()

            elif Packet.type == self.TEARDOWN:
                print("Fluxo eliminado da destination: " + source)
                # Passar pacote ao próximo nodo
                self.lock.acquire()

                oldStatus = self.streamsTable[RTSPPORT].stream_table_status()
                # Remover fluxo da tabela de rotas
                self.streamsTable[RTSPPORT].delete_stream(route[0])
                newStatus = self.streamsTable[RTSPPORT].stream_table_status()

                empty = self.streamsTable[RTSPPORT].is_empty()

                if empty:
                    rtsp = rtsp.encode(Packet.type, new_data)
                    self.rtspClientSocket.sendto(rtsp, (destination, RTSPPORT))
                elif oldStatus != newStatus:
                    rtsp = rtsp.encode(self.PAUSE, new_data)
                    self.rtspClientSocket.sendto(rtsp, (destination, RTSPPORT))
                self.lock.release()

    def RTP_handler(self, args):
        
        data, rtpClientSocket, RTSPPORT = args
        
        openStreams = self.streamsTable[RTSPPORT].get_streams()

        self.lock.acquire()
        for stream in openStreams:
            # print("Redirecionei pacote de stream " + source_ip + " -> " + stream.source)
            rtpClientSocket.sendto(
                data, (stream.destination_route[-2], stream.port)
            )
        self.lock.release()

    # Listening for RtspPacket
    def service_RTSP(self, args):

        RTSPPORT = args
        self.streamsTable[RTSPPORT] = StreamsTable()

        if RTSPPORT == 5555:
            self.rtspServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.rtspServerSocket.bind(("", RTSPPORT))

            # O nodo tem que mandar uma menssagem de registo
            HelloPacket = RtspPacket()
            HelloPacket = HelloPacket.encode(self.HELLO, "")

            self.rtspClientSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.rtspClientSocket.sendto(
                HelloPacket, (self.bootstrapperAddress, RTSPPORT)
            )
        else:
            rtspServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            rtspServerSocket.bind(("", RTSPPORT))

            self.socketsRTSP[RTSPPORT] = rtspServerSocket

        while True:

            if RTSPPORT == 5555:
                bytesAddressPair = self.rtspServerSocket.recvfrom(RTSP_BUFFER_SIZE)
            else:
                bytesAddressPair = self.socketsRTSP[RTSPPORT].recvfrom(RTSP_BUFFER_SIZE)

            # Aqui chamamos um handler para interpretar a msg e agir de acordo
            thread = Thread(target=self.RTSP_handler, args=(bytesAddressPair, RTSPPORT))
            thread.start()

        os._exit(0)

    def service_RTP(self, args):

        RTPPORT,RTSPPORT = args
        rtpClientSocket = ""
        if RTPPORT == 6666:
            self.rtpServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.rtpServerSocket.bind(("", RTPPORT))
            self.rtpClientSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            rtpClientSocket = self.rtpClientSocket
        else:
            rtpServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            rtpServerSocket.bind(("", RTPPORT))
            rtpClientSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.socketsRTP[RTPPORT] = rtpServerSocket

        while True:
            if RTPPORT == 6666:
                bytesAddressPair = self.rtpServerSocket.recvfrom(RTP_BUFFER_SIZE)
            else:
                bytesAddressPair = self.socketsRTP[RTPPORT].recvfrom(RTP_BUFFER_SIZE)

            data = bytesAddressPair[0]

            thread = Thread(target=self.RTP_handler, args=((data, rtpClientSocket, RTSPPORT),))
            thread.start()
        os._exit(0)
