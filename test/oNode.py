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
        elif args[0]=="-c":
            # Adicionar novo cliente à overlay:
            # oNode -c <bootstrapper_adress>
            client = ClientLauncher(bootstrapperAdressPort)
            client.run()
        elif args[0]=="-n":
            # Adicionar novo nodo à overlay:
            # oNode -n <bootstrapper_adress>
            node = Node(bootstrapperAdressPort)
            node.run()
        else: 
            print("ERROR")

    elif nArgs==3:
        if args[0]=="-s":
            bootstrapperAdress = args[1]
            bootstrapperAdressPort = (bootstrapperAdress,OLY_PORT)
            filename = args[2]
            # Adicionar novo server à overlay:
            # oNode -s <bootstrapper_adress>
            server = ServerLauncher(bootstrapperAdressPort, filename)
            server.run()
        else:
             print("ERROR")

    else: print("ERROR")