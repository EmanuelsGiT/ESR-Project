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
OLY_PORT = 5555
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

    def __init__(self, bootstrapperAddress, isRp, ports):
        self.bootstrapperAddress = bootstrapperAddress
        self.rp = ""
        self.isRp = isRp
        self.ports = ports
        self.socketsOLY = {}
        self.socketsRTP = {}
        self.streamsTable = {}
        self.neighbours = []
        self.lock = Lock()

    def run(self):
        print("--------------Node--------------")
        if self.isRp:
            self.route = Route("", MAX_DELTA, datetime.now().time())

        RTPPORT = RTP_PORT
        OLYPORT = OLY_PORT

        Thread(target=self.service_OLY, args=(OLYPORT,)).start()
        Thread(target=self.service_RTP, args=((RTPPORT,OLYPORT),)).start()
        Thread(target=self.service_OLY, args=(OLYPORT+1,)).start()
        Thread(target=self.service_RTP, args=((RTPPORT+1,OLYPORT+1),)).start()


    def OLY_handler(self, bytesAddressPair, OLYPORT):
        source = bytesAddressPair[1][0]
        msg = bytesAddressPair[0]

        Packet = OlyPacket()
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
                    old_source != new_source and self.streamsTable[OLYPORT].status == "open"
                ):  # TODO
                    print("Updated Source")
                    SetupPacket = OlyPacket()
                    SetupPacket = SetupPacket.encode("SETUP", [])
                    self.olyClientSocket.sendto(SetupPacket, (new_source, OLYPORT))

                    PlayPacket = OlyPacket()
                    PlayPacket = PlayPacket.encode("PLAY", [])
                    self.olyClientSocket.sendto(PlayPacket, (new_source, OLYPORT))

                    TDNPacket = OlyPacket()
                    TDNPacket = TDNPacket.encode("TEARDOWN", [])
                    self.olyClientSocket.sendto(TDNPacket, (old_source, OLYPORT))

            self.lock.release()
        else:
            if self.isRp:
                destination = self.route.source
            else:
                destination = self.neighbours[0]

            data = Packet.payload
            port = data[0]
            # source_ip = data
            route = data[1:]
            route.append(self.ip)

            oly = OlyPacket()
            new_data = data
            if not self.isRp:
                new_data.append(self.ip)

            if Packet.type == self.SETUP:
                print("Criei novo fluxo | destination: " + source)
                self.lock.acquire()
                # Preciso implementar mensagens de proba para conseguirmos saber isto
                # Adicionar um fluxo à routing table falta passar o dest (novo vizinho a qual o novo atual passa stream)
                firstStream = self.streamsTable[OLYPORT].is_empty()
                self.streamsTable[OLYPORT].add_stream(port, route[0], route)  # o destino da stream é a source de quem fez o pedido

                if firstStream:
                    oly = oly.encode(Packet.type, new_data)
                    self.olyClientSocket.sendto(oly, (destination, OLYPORT))
                    print("sending SETUP to " + destination)
                self.lock.release()

            elif Packet.type == self.PLAY:
                print("Fluxo ativo | destination: " + source)
                self.lock.acquire()
                oldStatus = self.streamsTable[OLYPORT].stream_table_status()
                self.streamsTable[OLYPORT].open_stream(route[0])
                newStatus = self.streamsTable[OLYPORT].stream_table_status()

                if oldStatus != newStatus:
                    oly = oly.encode(Packet.type, new_data)
                    self.olyClientSocket.sendto(oly, (destination, OLYPORT))
                    print("sending PLAY to " + destination)
                self.lock.release()

            elif Packet.type == self.PAUSE:
                print("Fluxo pausado | destination: " + source)
                self.lock.acquire()
                # Fecha o fluxo pois o nodo vizinhos(source_ip) não quer stream
                oldStatus = self.streamsTable[OLYPORT].stream_table_status()
                self.streamsTable[OLYPORT].close_stream(route[0])
                newStatus = self.streamsTable[OLYPORT].stream_table_status()

                if oldStatus != newStatus:
                    oly = oly.encode(Packet.type, new_data)
                    self.olyClientSocket.sendto(oly, (destination, OLYPORT))
                self.lock.release()

            elif Packet.type == self.TEARDOWN:
                print("Fluxo eliminado da destination: " + source)
                # Passar pacote ao próximo nodo
                self.lock.acquire()

                oldStatus = self.streamsTable[OLYPORT].stream_table_status()
                # Remover fluxo da tabela de rotas
                self.streamsTable[OLYPORT].delete_stream(route[0])
                newStatus = self.streamsTable[OLYPORT].stream_table_status()

                empty = self.streamsTable[OLYPORT].is_empty()

                if empty:
                    oly = oly.encode(Packet.type, new_data)
                    self.olyClientSocket.sendto(oly, (destination, OLYPORT))
                elif oldStatus != newStatus:
                    oly = oly.encode(self.PAUSE, new_data)
                    self.olyClientSocket.sendto(oly, (destination, OLYPORT))
                self.lock.release()

    def RTP_handler(self, args):
        
        data, rtpClientSocket, OLYPORT = args
        
        openStreams = self.streamsTable[OLYPORT].get_streams()

        self.lock.acquire()
        for stream in openStreams:
            # print("Redirecionei pacote de stream " + source_ip + " -> " + stream.source)
            rtpClientSocket.sendto(
                data, (stream.destination_route[-2], stream.port)
            )
        self.lock.release()

    # Listening for OlyPacket
    def service_OLY(self, args):

        OLYPORT = args
        self.streamsTable[OLYPORT] = StreamsTable()

        if OLYPORT == 5555:
            self.olyServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.olyServerSocket.bind(("", OLYPORT))

            # O nodo tem que mandar uma menssagem de registo
            HelloPacket = OlyPacket()
            HelloPacket = HelloPacket.encode(self.HELLO, "")

            self.olyClientSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            self.olyClientSocket.sendto(
                HelloPacket, (self.bootstrapperAddress, OLYPORT)
            )
        else:
            olyServerSocket = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            olyServerSocket.bind(("", OLYPORT))

            self.socketsOLY[OLYPORT] = olyServerSocket

        while True:

            if OLYPORT == 5555:
                bytesAddressPair = self.olyServerSocket.recvfrom(OLY_BUFFER_SIZE)
            else:
                bytesAddressPair = self.socketsOLY[OLYPORT].recvfrom(OLY_BUFFER_SIZE)

            # Aqui chamamos um handler para interpretar a msg e agir de acordo
            thread = Thread(target=self.OLY_handler, args=(bytesAddressPair, OLYPORT))
            thread.start()

        os._exit(0)

    def service_RTP(self, args):

        RTPPORT,OLYPORT = args
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
            print(data)

            thread = Thread(target=self.RTP_handler, args=((data, rtpClientSocket, OLYPORT),))
            thread.start()
        os._exit(0)
