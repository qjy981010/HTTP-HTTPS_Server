# -*- coding:UTF-8 -*-

import socket
import threading
import time
import os
import ssl
from data import content_type, status_code

lock = threading.Lock()    # use the lock to control the threads
path = os.getcwd()


def server(connect, address, s_ssl=None):      # handle the request
    if s_ssl:
        print('Accept HTTPS request from %s:%s' % address)
    else:
        print('Accept HTTP request from %s:%s' % address)
    while True:
        try:
            request = connect.recv(1024).decode('utf-8')
        except BlockingIOError:
            continue
        except ConnectionResetError:
            print('The client closed an existing connection forcibly.')
        lock.acquire()
        print(request)
        time.sleep(0.1)
        if not request:
            lock.release()
            break
        method = request.split(' ')[0]
        src = request.split(' ')[1].split('?')[0]
        if method == 'GET' or method == 'POST':
            if src[0] != '/':
                with open(path+'/web/411.html', 'rb') as f:
                    status = 411
                    ftype = 'tml'
                    data = f.read()
            else:
                try:
                    if src == '/' or src == '/web' or src == '/web/':
                        src = '/web/index.html'
                    ftype = src[-3:]
                    with open(path+src, 'rb') as f:
                        status = 200
                        data = f.read()
                except FileNotFoundError:
                    with open(path+'/web/404.html', 'rb') as f:
                        status = 404
                        ftype = 'tml'
                        data = f.read()
        else:
            continue
        response = '''HTTP/1.1 {0} {1}\nContent-Type: {2}\n\n'''.format(status, status_code[status], content_type[ftype])
        response = bytes(response, 'UTF-8') + data
        connect.sendall(response)
        lock.release()
    connect.close()
    print('Connection from %s:%s closed\n' % address)


def https_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(0)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 9999))
    s.listen(10)
    print('Waiting for HTTPS request...\n')
    s_ssl = ssl.wrap_socket(
        s,
        keyfile='privkey.pem',
        certfile='cacert.pem',
        server_side=True
    )
    while True:
        try:
            conn, addr = s_ssl.accept()
            s_ssl.setblocking(0)
        except BlockingIOError:
            continue
        ts = threading.Thread(target=server, args=[conn, addr, s_ssl])
        ts.start()


if __name__ == '__main__':

    thttps = threading.Thread(target=https_server, args=[])    # use a new thread to handle HTTPS request
    thttps.setDaemon(True)
    thttps.start()

    HOST, PORT = '127.0.0.1', 8888

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind((HOST, PORT))
    sock.listen(10)
    print('Waiting for HTTP request...\n')
    
    while True:
        try:
            connect, address = sock.accept()
            connect.setblocking(0)
        except BlockingIOError:
            continue
        t = threading.Thread(target=server, args=[connect, address])
        t.start()

