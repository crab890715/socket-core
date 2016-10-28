# -*- coding: utf-8 -*-
'''
Created on 2016年10月22日

@author: kingdee
'''
import eventloop, socket, errno, traceback, logging
from macpath import join
STEP_INIT = 0
STEP_DESTROYED = -1

BUF_SIZE = 32 * 1024


class SockHandler(object):
    sock = None
    sock_type = None
    def handler(self, sock, fd, event):
        pass

class  SockManage(object):
    loop = eventloop.EventLoop()
    @staticmethod
    def start():
        SockManage.loop.run()
    @staticmethod
    def remove(sock):
        SockManage.loop.remove(sock)
    @staticmethod
    def add(sock, mode=eventloop.POLL_IN | eventloop.POLL_ERR):
        SockManage.loop.add(sock, mode)
        pass
    @staticmethod
    def modify(sock, mode=eventloop.POLL_IN | eventloop.POLL_ERR):
        SockManage.loop.modify(sock, mode)
class DNSResolver(SockHandler):
    _this = None
    def __init__(self):
        self.sock_type = "resolver"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                   socket.SOL_UDP)
        self.sock.setblocking(False)
        SockManage.add(self, eventloop.POLL_IN | eventloop.POLL_ERR)
        self._this = self
    def handler(self, sock, fd, event):
        data, addr = sock.recvfrom(1024)
        print data
        pass
    def resolve(self, hostname, callback):
        self.sock.sendto("test",("8.8.8.8",53))
        self.sock.sendto("test",("8.8.4.4",53))
        pass
    @staticmethod
    def instance():
        if not DNSResolver._this :
            DNSResolver._this = DNSResolver()
        return DNSResolver._this
class RemoteSockHandler(SockHandler):
    def __init__(self, data, local_sock_handler):
        self.local_sock_handler = local_sock_handler
        ip, port = self.parse_header(data)
        print ip,port
        addrs = socket.getaddrinfo(ip, port, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP)
        if len(addrs) == 0:
            raise Exception("getaddrinfo failed for %s:%d" % (ip, port))
        print addrs
        af, socktype, proto, canonname, sa = addrs[0]
        remote_sock = socket.socket(af, socktype, proto)
        remote_sock.setblocking(False)
#         remote_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.sock = remote_sock
        self.sock_type = "remote"
        try:
            self.sock.connect((ip,port))
        except (OSError, IOError) as e:
            traceback.print_exc()
            if eventloop.errno_from_exception(e) == \
                    errno.EINPROGRESS:
                pass
        self.sock.sendall(data)
        SockManage.add(self, eventloop.POLL_ERR | eventloop.POLL_OUT)
    def parse_header(self, data):
        lines = data.splitlines()
        line = lines[1]
        arr = line.strip()[6:].split(":")
        if(len(arr) > 1):
            host = arr[0]
            port = int(arr[1])
        else:
            host = arr[0]
            port = 80
        return (host, port)
    def _on_remote_error(self):
        self.destroy()
        pass
    def _on_remote_read(self):
        
        pass
    def _on_remote_write(self):
        data = None
        try:
            data = self.sock.recv(BUF_SIZE)
            print data
            if data:
                self.local_sock_handler.sock.send(data)
            if not data :
                self.destroy()
                pass
        except (OSError, IOError) as e:
            if eventloop.errno_from_exception(e) in \
                    (errno.ETIMEDOUT, errno.EAGAIN, errno.EWOULDBLOCK):
                return
            self.destroy()
        pass
    def handler(self, sock, fd, event):
        if event & eventloop.POLL_ERR:
            self._on_remote_error()
        if event & (eventloop.POLL_IN | eventloop.POLL_HUP):
            self._on_remote_read()
        if event & eventloop.POLL_OUT:
            self._on_remote_write()
        else:
            print 'unknown socket'
    def destroy(self):
        SockManage.remove(self)
        pass
class LocalSockHandler(SockHandler):
    def __init__(self, sock):
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.sock = sock
        self.sock_type = "sock"
        self.data = [];
        SockManage.add(self, eventloop.POLL_IN | eventloop.POLL_ERR)
        pass
    def _on_local_error(self):
        self.destroy()
        pass
    def _on_local_read(self):
        data = None
        try:
            data = self.sock.recv(BUF_SIZE)
            print data
            self.data.append(data)
            context = "".join(self.data)
            if not data and context.strip():
                RemoteSockHandler(context, self);
                self.destroy()
        except (OSError, IOError) as e:
            if eventloop.errno_from_exception(e) in \
                    (errno.ETIMEDOUT, errno.EAGAIN, errno.EWOULDBLOCK):
                return
            self.destroy()
    def _on_local_write(self):
        pass
    def handler(self, sock, fd, event):
        if event & eventloop.POLL_ERR:
            print "******************1***********************"
            self._on_local_error()
            return
        if event & (eventloop.POLL_IN | eventloop.POLL_HUP):
            print "******************2***********************"
            self._on_local_read()
            return
        if event & eventloop.POLL_OUT:
            print "******************3***********************"
            self._on_local_write()
        else:
            print 'unknown socket'
    def destroy(self):
        SockManage.remove(self)
        pass
class LocalServerHandler(SockHandler):
    def __init__(self, ip, port):
        addrs = socket.getaddrinfo(ip, port, 0,
                                   socket.SOCK_STREAM, socket.SOL_TCP)
        if len(addrs) == 0:
            raise Exception("can't get addrinfo for %s:%d" % 
                            (ip, port))
        af, socktype, proto, canonname, sa = addrs[0]
        server_socket = socket.socket(af, socktype, proto)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(sa)
        server_socket.setblocking(False)
        server_socket.listen(1024)
        self.sock = server_socket
        self.sock_type = "server"
        pass
    def handler(self, sock, fd, event):
        if event & eventloop.POLL_ERR:
            raise Exception('server_socket error')
        if event & eventloop.POLL_IN:
            try:
                conn = self.sock.accept()
                LocalSockHandler(conn[0])
            except (OSError, IOError) as e:
                logging.error(e)
                traceback.print_exc()
def demo ():
    pass
if __name__ == '__main__':
#     local_server = LocalServer()
#     loop = eventloop.EventLoop()
#     local_server.add_to_loop(loop)
#     loop.run()
#     print "\x05\00"
#     print ord("\x05")
    
    SockManage.add(LocalServerHandler("127.0.0.1", 1080), eventloop.POLL_IN | eventloop.POLL_ERR)
    SockManage.start()
    pass
