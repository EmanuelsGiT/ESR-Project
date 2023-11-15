from server.server import Server


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        #print(f"Usage: {sys.argv[0].split('/')[-1]} <port>")
        exit(-1)
    try:
        host = sys.argv[1]
        port = int(sys.argv[2])
    except ValueError:
        raise ValueError('host/port value should be integer')

    while True:
        server = Server(host, port)
        try:
            server.setup()
            server.handle_rtsp_requests()
        except ConnectionError as e:
            server.server_state = server.STATE.TEARDOWN
            print(f"Connection reset: {e}")
