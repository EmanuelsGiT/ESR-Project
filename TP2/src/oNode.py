from threading import Thread
import sys
from Node import *
from ServerLauncher import *
from ClientLauncher import *
from Bootstrapper import *
from RtspPacket import *


if __name__ == "__main__":
    args = sys.argv[1:]
    nArgs = len(args)

    if nArgs == 2:
        bootstrapperAdress = args[1] 
        bootstrapperAdressPort = bootstrapperAdress
        # Iniciar bootstrapper:
        # oNode -bs <config_file>
        if args[0]=="-bs":
            print("------------Bootstrapper------------")
            bootstrapper = Bootstrapper(args[1])
            bootstrapper.run()
    elif args[0]=="-s":
        bootstrapperAdress = args[1]
        bootstrapperAdressPort = (bootstrapperAdress,RTSP_PORT)
        movies = args[2:]
        # Adicionar novo server à overlay:
        # oNode -s <bootstrapper_adress> movie1 ...
        server = ServerLauncher(bootstrapperAdressPort, movies)
        server.run()

    elif nArgs == 3: 
        bootstrapperAdress = args[1]
        if args[0]=="-n":  
            # Adicionar novo nodo à overlay:
            # oNode -n <bootstrapper_adress> nmovies
            isRp = False
            nmovies = args[2]
            node = Node(bootstrapperAdress, isRp, nmovies)
            node.run()
        elif args[0]=="-rp":
            # Adicionar novo nodo à overlay:
            # oNode -n <bootstrapper_adress> nmovies
            isRp = True
            nmovies = args[2]
            node = Node(bootstrapperAdress, isRp, nmovies)
            node.run()

    elif nArgs == 4: 
        if args[0]=="-c":
            bootstrapperAdress = args[1]
            bootstrapperAdressPort = (bootstrapperAdress,RTSP_PORT)
            # Adicionar novo cliente à overlay:
            # oNode -c <bootstrapper_adress> rtpport rtspport
            rtp_port = args[2]
            rtsp_port = args[3]
            client = ClientLauncher(bootstrapperAdressPort, rtp_port, rtsp_port)
            client.run()

    else: print("ERROR: Invalid Args")