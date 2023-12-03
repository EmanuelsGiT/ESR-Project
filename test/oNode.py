from threading import Thread
import sys
from Node import *
from ServerLauncher import *
from ClientLauncher import *
from Bootstrapper import *
from OlyPacket import *


if __name__ == "__main__":
    args = sys.argv[1:]
    nArgs = len(args)

    if nArgs==2:
        bootstrapperAdress = args[1]
        bootstrapperAdressPort = (bootstrapperAdress,OLY_PORT)
        # Iniciar bootstrapper:
        # oNode -bs <config_file>
        if args[0]=="-bs":
            print("------------Bootstrapper------------")
            bootstrapper = Bootstrapper(args[1])
            bootstrapper.run()
        elif args[0]=="-n":
            # Adicionar novo nodo à overlay:
            # oNode -n <bootstrapper_adress>
            isRp = False
            node = Node(bootstrapperAdressPort, isRp)
            node.run()
        elif args[0]=="-rp":
            # Adicionar novo nodo à overlay:
            # oNode -n <bootstrapper_adress>
            isRp = True
            node = Node(bootstrapperAdressPort, isRp)
            node.run()
        else: 
            print("ERROR")

    elif nArgs==3:
        if args[0]=="-s":
            bootstrapperAdress = args[1]
            bootstrapperAdressPort = (bootstrapperAdress,OLY_PORT)
            movies = args[2:]
            # Adicionar novo server à overlay:
            # oNode -s <bootstrapper_adress>
            server = ServerLauncher(bootstrapperAdressPort, movies)
            server.run()
        elif args[0]=="-c":
            bootstrapperAdress = args[1]
            bootstrapperAdressPort = (bootstrapperAdress,OLY_PORT)
            # Adicionar novo cliente à overlay:
            # oNode -c <bootstrapper_adress>
            movie = args[2]
            client = ClientLauncher(bootstrapperAdressPort, movie)
            client.run()
        else:
             print("ERROR")

    else: print("ERROR")