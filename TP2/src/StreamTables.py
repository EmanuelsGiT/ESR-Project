from threading import Lock

# Stream, guarda detalhes de um fluxo de stream
class Stream:
    def __init__(self,port,destination,destination_route):
        self.port = int(port)
        self.destination = destination
        self.destination_route = destination_route
        self.state = "closed"


# Table de streaming, guarda conjunto de fluxos de streams
class StreamsTable:

    def __init__(self):
        self.lock = Lock()
        self.streams = []
        self.status = "closed"

    def is_empty(self):
        self.lock.acquire()
        try:
            return len(self.streams) == 0
        finally:
            self.lock.release()


    def stream_table_status(self):
        self.lock.acquire()
        try:
            return self.status
        finally:
            self.lock.release()

    def add_stream(self,port,destination,destination_route):
        self.lock.acquire()
        try:
            self.streams.append(Stream(port,destination,destination_route))
        finally:
            self.lock.release()

    def open_stream(self,destination):
        self.lock.acquire()
        try:
            for stream in self.streams:
                if(stream.destination==destination):
                    stream.state = "open"
                    if(self.status != "open"):
                        self.status = "open"
        finally:
            self.lock.release()

    def check_status(self):
        close = True
        for stream in self.streams:
            if(stream.state == "open"):
                close  = False
        if(close):
            self.status = "closed"


    def close_stream(self,destination):
        self.lock.acquire()
        try:
            for stream in self.streams:
                if(stream.destination==destination):
                    stream.state = "closed"
            self.check_status()
        finally:
            self.lock.release()

    def delete_stream(self,destination):
        self.lock.acquire()
        try:
            for stream in self.streams:
                if(stream.destination==destination):
                    self.streams.remove(stream)
            if(self.status != "closed"):
                self.check_status()
        finally:
            self.lock.release()

    def get_streams(self):
        self.lock.acquire()
        try:
            open_entries = []
            for stream in self.streams:
                if(stream.state=="open"):
                    open_entries.append(stream)
            return open_entries
        finally:
            self.lock.release()


