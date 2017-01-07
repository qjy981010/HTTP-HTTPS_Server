import queue
import socket
import select
import threading
import time
import os
import ssl
from data import content_type, status_code
from concurrent.futures import ThreadPoolExecutor


def close(s, ioelist):
    lock.acquire()
    if s in ioelist[1]:
        ioelist[1].remove(s)
    if s in ioelist[0]:
        print('closing ', s.getpeername())
        ioelist[0].remove(s)
        s.close()
        if ioe.qsize() > 1:
            ioe.get()
    if s in ioelist[2]:
        ioelist[2].remove(s)
    lock.release()


def http_server():                                  # create a http-server on port 8888
    host, port = '127.0.0.1', 8888
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setblocking(0)
    s.bind((host, port))
    s.listen(1024)
    return s


def https_server():                                 # create a https-server on port 9999
    host, port = '127.0.0.1', 9999
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind((host, port))
    sock.listen(1024)
    s_ssl = ssl.wrap_socket(
        sock,
        keyfile='privkey.pem',
        certfile='cacert.pem',
        server_side=True
    )
    return s_ssl


def server():                                       # handle the requests
    while True:
        ioelist = ioe.get()
        rlist, wlist, elist = select.select(ioelist[0], ioelist[1], ioelist[2])
        for r in rlist:                                                             # accept requests
            if r == http or r == https:
                try:
                    connect, address = r.accept()
                except BlockingIOError:
                    break
                if connect not in ioelist[0]:
                    pool.submit(server, )
                    ioe.put(ioelist)
                print('Accept request from ', address, ' in ', threading.current_thread().name)
                ioelist[3][connect] = queue.Queue()
                connect.setblocking(0)
                ioelist[0].append(connect)
            else:
                try:
                    request = r.recv(1024).decode('utf-8')
                except BlockingIOError:
                    break
                except ConnectionResetError:
                    print('The connection with ', r.getpeername(), ' was closed by the client.')
                    close(r, ioelist)
                    continue
                except OSError:
                    continue
                print(request)
                time.sleep(0.1)
                if not request:
                    close(r, ioelist)
                    continue
                ioelist[3][r].put(request)
                if r not in ioelist[1]:
                    ioelist[1].append(r)

        for w in wlist:                                             # send responses
            try:
                request = ioelist[3][w].get(block=0)
            except queue.Empty:
                ioelist[1].remove(w)
            else:
                method = request.split(' ')[0]
                src = request.split(' ')[1].split('?')[0]
                if method == 'GET' or method == 'POST':
                    if src[0] != '/':
                        with open(path + '/web/411.html', 'rb') as f:
                            status = 411
                            ftype = 'tml'
                            data = f.read()
                    else:
                        try:
                            if src == '/' or src == '/web' or src == '/web/':
                                src = '/web/index.html'
                            ftype = src[-3:]
                            with open(path + src, 'rb') as f:
                                status = 200
                                data = f.read()
                        except FileNotFoundError:
                            with open(path + '/web/404.html', 'rb') as f:
                                status = 404
                                ftype = 'tml'
                                data = f.read()
                else:
                    continue
                response = 'HTTP/1.1 {0} {1}\nContent-Type: {2}\n\n'.format(status, status_code[status],
                                                                            content_type[ftype])
                response = bytes(response, 'UTF-8') + data
                ioelist[4][w] = [response]
                try:
                    intsent = 0
                    ioelist[4][w].append(intsent)
                    while len(ioelist[4][w][0][ioelist[4][w][1]:]) > 0:       # in this way cilents can download data
                        ioelist[4][w][1] = w.send(ioelist[4][w][0][ioelist[4][w][1]:])           # from this server
                        rate = 100 * (ioelist[4][w][1] // (len(ioelist[4][w][0]) - 1))
                        print('sending...\t\t\t\t\t\t\t\t\t\t\t\t['+'#'*rate+(100-rate)*' '+']'+str(rate)+'%\r')
                        # response = response[intsent:]
                    time.sleep(1)
                    if 'text/html' not in request:
                        close(w, ioelist)
                except ConnectionResetError:
                    break

        for e in elist:                                          # handle errors
            print(" exception condition on ", e.getpeername())
            close(e, ioelist)
            del ioelist[3][e]
            e.close()

        ioe.put([ioelist[0], ioelist[1], ioelist[2], ioelist[3], ioelist[4]])


if __name__ == '__main__':
    path = os.getcwd()
    http = http_server()
    https = https_server()
    inputs = [http, https]
    outputs = []
    ioe = queue.Queue()
    lock = threading.Lock()
    ioe.put([inputs, outputs, [], {}, {}])
    pool = ThreadPoolExecutor(128)
    print('Waiting for requests...')
    server()

