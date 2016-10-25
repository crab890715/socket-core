# -*- coding: utf-8 -*-
'''
Created on 2016年10月22日

@author: kingdee
'''
import eventloop, socket,errno,traceback,logging
STEP_INIT = 0
STEP_DESTROYED = -1

BUF_SIZE = 32 * 1024


class  SockManage(object):
    loop = eventloop.EventLoop()
    @staticmethod
    def start():
        SockManage.loop.run()
    @staticmethod
    def remove(sock):
        SockManage.loop.remove(sock)
    @staticmethod
    def add(sock):
        SockManage.loop.add(sock,eventloop.POLL_IN | eventloop.POLL_ERR)
        pass
class RemoteSock(object):
    def __init__(self,ip,port):
        addrs = socket.getaddrinfo(ip, port, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP)
        if len(addrs) == 0:
            raise Exception("getaddrinfo failed for %s:%d" % (ip,  port))
        af, socktype, proto, canonname, sa = addrs[0]
        remote_sock = socket.socket(af, socktype, proto)
        self._remote_sock = remote_sock
        self._sock_queue[remote_sock.fileno()] = self
        remote_sock.setblocking(False)
        remote_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
class LocalSock(object):
    def __init__(self, sock):
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        SockManage.add({"sock":sock,"type":"sock","callback":self._handle_event})
        pass
    def _create_remote_socket(self, ip, port):
        addrs = socket.getaddrinfo(ip, port, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP)
        if len(addrs) == 0:
            raise Exception("getaddrinfo failed for %s:%d" % (ip,  port))
        af, socktype, proto, canonname, sa = addrs[0]
        remote_sock = socket.socket(af, socktype, proto)
        self._remote_sock = remote_sock
        self._sock_queue[remote_sock.fileno()] = self
        remote_sock.setblocking(False)
        remote_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        return remote_sock
    def _on_remote_error(self):
        self.destroy()
        pass
    def _on_remote_read(self):
        
        pass
    def _on_remote_write(self):
        pass
    def _on_local_error(self):
        self.destroy()
        pass
    def _on_local_read(self):
        if not self._local_sock:
            return
        data = None
        try:
            data = self._local_sock.recv(BUF_SIZE)
        except (OSError, IOError) as e:
            if eventloop.errno_from_exception(e) in \
                    (errno.ETIMEDOUT, errno.EAGAIN, errno.EWOULDBLOCK):
                return
        if not data:
            self.destroy()
            return
        if self._step == STEP_INIT:
            self._handle_stage_hello(data)
        pass
    def _on_local_write(self):
        pass
    def _handle_event(self, sock, event):
        if event & eventloop.POLL_ERR:
            self._on_local_error()
            if self._step == STEP_DESTROYED:
                return
        if event & (eventloop.POLL_IN | eventloop.POLL_HUP):
            self._on_local_read()
            if self._step == STEP_DESTROYED:
                return
        if event & eventloop.POLL_OUT:
            self._on_local_write()
        else:
            print 'unknown socket'
    def destroy(self):
        if self._stage == STEP_DESTROYED:
            return
        self._stage = STEP_DESTROYED
        if self._remote_sock:
            try:
                self._loop.remove(self._remote_sock)
                del self._sock_queue[self._remote_sock.fileno()]
                self._remote_sock.close()
                self._remote_sock = None
            except:
                pass
        if self._local_sock:
            try:
                self._loop.remove(self._local_sock)
                del self._sock_queue[self._local_sock.fileno()]
                self._local_sock.close()
                self._local_sock = None
            except:
                pass
class LocalServer(object):
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
        SockManage.add({"sock":server_socket,"type":"server","callback":self._handle_event})
        pass
    def _handle_event(self,sock, fd, event):
        if sock['sock']:
            if event & eventloop.POLL_ERR:
                raise Exception('server_socket error')
            try:
                conn = sock['sock'].accept()
                LocalSock(conn[0])
            except (OSError, IOError) as e:
                logging.error(e)
                traceback.print_exc()
if __name__ == '__main__':
#     local_server = LocalServer()
#     loop = eventloop.EventLoop()
#     local_server.add_to_loop(loop)
#     loop.run()
#     print "\x05\00"
#     print ord("\x05")
    LocalServer()
    SockManage.start()
    a = {"a":1,"b":2,"c":3}
    print a['a']
    pass
