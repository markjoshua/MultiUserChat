import sys
import socket
import select
from optparse import OptionParser

#process options using OptionParser
def processOptions(argv):
    global opts
    global args

    try:
        parser = OptionParser()
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="Set verbosity")
        parser.add_option("-a", "--addr", dest="addr", action="store", help="Set server listen address [default:\"%default\"]")
        parser.add_option("-p", "--port", dest="port", action="store", type="int", help="Set server listen port [default:%default]")
        parser.add_option("-b", "--backlog", dest="backlog", action="store", type="int", help="Set server connection backlog [default:%default]")

        parser.set_defaults(addr="127.0.0.1", port="6666", backlog="5")

        (opts, args) = parser.parse_args(argv)

    except Exception, e:
        sys.stderr.write("Error processing options; for help use --help")
        return 2

    if opts.verbose > 0:
        print "Verbose"
        print "args=", args
    if opts.verbose > 0 and opts.addr:
        print "addr=", opts.addr
    if opts.verbose > 0 and opts.port:
        print "port=", str(opts.port)
    if opts.verbose > 0 and opts.backlog:
        print "backlog=", str(opts.backlog)

#Given options like address, port, and backlog, set up a listen socket for
#the server
def setupServerSocket(opts):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((opts.addr, opts.port))
        s.listen(opts.backlog)
        return s
    except socket.error, msg:
        print "Failed to create/bind socket. Error code: %d, Error message: %s" % (msg[0],msg[1])
        sys.exit(1)

#Helper function to close any remaining open sockets
def cleanup(clients, listenSocket):
    for key in clients:
        try:
            clients[key].shutdown(SHUT_RDWR)
            clients[key].close()
        except:
            clients[key].close()
    try:
        listenSocket.shutdown(socket.SHUT_RDWR)
        listenSocket.close()
    except:
        listenSocket.close()

#reliably read a line at a time from a socket, delineated by \n
def recv_line(s):
    buffer = ""
    try:
        ch = s.recv(1)
    except:
        return buffer
    try:
        while ch != "\n" and ch != "":
            buffer += ch
            ch = s.recv(1)
    except:
        return ""
    
    if ch == "":
        buffer = ""
    else:
        buffer += "\n"
    return buffer 

#handle client interactions
def processClient(client, clients, aliases, fd):
    line = recv_line(client)
    if line == "":
        if fd not in aliases:
            if opts.verbose > 0:
                print "%d close before proper logon" % fd
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                client.close()
                
            return -1
        else:
            if opts.verbose > 0:
                print "%d logged off" % fd
                
            logoff_msg = aliases[fd][:len(aliases[fd])-1] + " has logged off.\n"
            for key in clients:
                clients[key].sendall(logoff_msg)
            aliases.pop(fd)
            
            return -1
    elif line == "\r\n":
        line = recv_line(client)
        if line == "":
            if opts.verbose > 0:
                print "%d improper alias" % fd
                
            errmsg = "Not acceptable alias\r\n"
            client.sendall(errmsg)
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                client.close()
                
            return -1
        else:
            aliases[fd] = line
            logon_msg = line[:len(line)-1] + " has logged on.\n"
            for key in clients:
                clients[key].sendall(logon_msg)
    else:
        if fd not in aliases:
            if opts.verbose > 0:
                print "%d attempted to message before logon" % fd
                
            errmsg = "Improper logon attempt\r\n"
            client.sendall(errmsg)
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                client.close()
                
            return -1
        else:
            line = aliases[fd][:len(aliases[fd])-1] + ": " + line
            for key in clients:
                clients[key].sendall(line)
            return 0

def main(argv=None):
    global opts

    if argv is None:
        processOptions(sys.argv[1:])
    else:
        processOptions(argv)

    listenSocket = setupServerSocket(opts)

    pollObject = select.poll()
    pollObject.register(sys.stdin, select.POLLIN)
    pollObject.register(listenSocket, select.POLLIN)
    clients = {}
    aliases = {}

    running = True
    while running:
        if opts.verbose > 0:
            print "Awaiting input from stdin or listenSocket port %d" % opts.port

        readylist = pollObject.poll()
        for (fd, event) in readylist:
            if fd == listenSocket.fileno():
                assert(event == select.POLLIN)
                if opts.verbose > 0:
                    print "Poll in from listenSocket"

                clientSocket, addr = listenSocket.accept()
                if opts.verbose > 0:
                    print "Connected with %s:%d" % (addr[0],addr[1])

                pollObject.register(clientSocket, select.POLLIN)
                clients[clientSocket.fileno()] = clientSocket
            elif fd == sys.stdin.fileno():
                if opts.verbose > 0:
                    print "Poll in from stdin"
                    
                stdin_input = sys.stdin.readline()
                if stdin_input == "exit\n":
                    running = False
                    cleanup(clients, listenSocket)
            else:
                client = clients[fd]
                result = processClient(client, clients, aliases, fd)
                if result == -1:
                    clients.pop(fd)
                    pollObject.unregister(fd)

    return

if __name__ == "__main__":
    sys.exit(main())
                


