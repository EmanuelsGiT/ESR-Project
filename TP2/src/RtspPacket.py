# Packet de comunicação de rede overlay
"""
RtspPacket implementa mensagens de controlo da rede overlay. As mensagens são em formato string, e os seus campos
são de parados por ';'. Um Rtsppacket tem um tamanho fixo de 250 bytes.

TYPE:
    HELLO -> Hello packet, pacote de registo no bootstrapper
    HELLORESPONSE -> Hello response, pacote de resposta ao Hello
    PROBE -> Probe packet, pacote de proba
    SETUP -> Setup packet
    PLAY -> Play packet
    PAUSE -> Pause packet
    TEARDOWN -> Teardown packet
PAYLOAD:
    O payload só terá valores quando o TYPE for HELLORESPONSE ou PROBE. O PAYLOAD tem os seus valores separados
pelo caracter ",".

"""

RTSP_BUFFER_SIZE = 250
RTSP_PORT = 5555

class RtspPacket:

    def __init__(self):
        pass

    def encode(self,type,payload):
        data = type + ";"

        if payload:
            # O payload tem que ser sempre uma lista
            for value in payload:
                data = data + str(value) + ","

            # Tira a virgula em excesso e acrescentar último separador
            data = data[:-1] + ";"
        else:
            # Se o payload for vazio
            data += ";"
        # Adiciona padding até atingir o tamanho de 250
        data.ljust(250,"0")
        return data.encode("utf-8")

    def decode(self,bytearray):
        data = bytearray.decode("utf-8")
        dataFields = data.split(";")

        # Tipo o pacote
        self.type = dataFields[0]
        # Array com os valores o payload
        self.payload = dataFields[1].split(",")

        return self
