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