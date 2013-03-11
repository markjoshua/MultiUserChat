from Tkinter import *
import tkMessageBox
import ttk
import socket
import threading
import select
import sys

class Server:
    def __init__(self, addr = '', port = 6666, my_alias = "Anon", serv_alias = None):
        self.addr = addr
        self.port = port
        self.my_alias = my_alias
        if serv_alias is None:
            self.serv_alias = addr
        else:
            self.serv_alias = serv_alias

class workerThread(threading.Thread):
    def __init__(self, sock, window, text_box):
        threading.Thread.__init__(self)
        self.sock = sock
        self.window = window
        self.text_box = text_box

    def run(self):
        self.text_box.config(state="disabled")
        
        pollObject = select.poll()
        pollObject.register(self.sock, select.POLLIN)

        running = True
        while running:
            readylist = pollObject.poll()
            for (fd,event) in readylist:
                if fd == self.sock.fileno():
                    line = recv_line(self.sock)
                    if line == "":
                        running = False
                    else:
                        self.text_box.config(state="normal")
                        self.text_box.insert("end", line)
                        self.text_box.config(state="disabled")
        if self.window:
            self.window.destroy()
            

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

def addServer(window, addr, port, alias, my_alias, servers, lbox):
    if port == "":
        tkMessageBox.showinfo(title="Error",message="Must enter a port number")
    elif my_alias == "":
        tkMessageBox.showinfo(title="Error",message="Must enter an alias(username)")
    else:
        if alias != "Optional":
            if alias in servers:
                tkMessageBox.showinfo(title="Error",message="Server alias already in use")
            else:
                try:
                    new_serv = Server(addr, int(port), my_alias, alias)
                    servers[alias] = new_serv
                    lbox.insert("end", alias)
                    window.destroy()
                except:
                    tkMessageBox.showinfo(title="Error",message="One or more fields are incorrect.")
        else:
            if addr in servers:
                tkMessageBox.showinfo(title="Error",message="Server alias already in use")
            else:
                try:
                    new_serv = Server(addr, int(port), my_alias)
                    servers[addr] = new_serv
                    lbox.insert("end", addr)
                    window.destroy()
                except:
                    tkMessageBox.showinfo(title="Error",message="One or more fields are incorrect.")

def newServer(servers, lbox):
    w = Toplevel(root)
    w.title("Add Server")
    frame = ttk.Frame(w, padding=(12,12,0,0))

    #labels
    add_lbl = ttk.Label(frame, text="Enter address:")
    prt_lbl = ttk.Label(frame, text="Enter port num:")
    my_alias_lbl = ttk.Label(frame, text="Enter your alias(username):")
    alias_lbl = ttk.Label(frame, text="Enter an alias for the server:")

    #entry widgets
    add_entry = ttk.Entry(frame)
    prt_entry = ttk.Entry(frame)
    my_alias_entry = ttk.Entry(frame)
    alias_entry = ttk.Entry(frame)

    #buttons
    accept_but = ttk.Button(frame, text="Accept", command=lambda:
                            addServer(w,add_entry.get(), prt_entry.get(),
                                      alias_entry.get(), my_alias_entry.get(), servers, lbox))
    cancel_but = ttk.Button(frame, text="Cancel", command=lambda: w.destroy())

    #set up grid for widgets
    frame.grid(column=0, row=0, sticky=(N,W,E,S))
    add_lbl.grid(column=0,row=0, sticky=(N,W,E,S))
    add_entry.grid(column=0,row=1, sticky=(N,W,E,S))
    prt_lbl.grid(column=0,row=2, sticky=(N,W,E,S))
    prt_entry.grid(column=0,row=3, sticky=(N,W,E,S))
    my_alias_lbl.grid(column=0,row=4, sticky=(N,W,E,S))
    my_alias_entry.grid(column=0,row=5, sticky=(N,W,E,S))
    alias_lbl.grid(column=0,row=6, sticky=(N,W,E,S))
    alias_entry.grid(column=0,row=7, sticky=(N,W,E,S))
    accept_but.grid(column=1,row=8,padx=12,pady=12, sticky=(N,W,E,S))
    cancel_but.grid(column=1,row=9,padx=12,pady=12, sticky=(N,W,E,S))

    w.columnconfigure(0, weight=1)
    w.rowconfigure(0, weight=1)
    frame.columnconfigure("all", weight=1)
    frame.rowconfigure("all", weight=1)

    #mark alias as optional
    alias_entry.delete(0, "end")
    alias_entry.insert(0, "Optional")

def selectServer(servers, lbox):
    #set up host socket with port num between 5000 and 6000
    host_port = 5000
    host = setupHost(host_port)
    count = 0
    while host == -1 and count < 1000:
        host_port += 1
        host = setupHost(host_port)
    if count == 1000:
        tkMessageBox.showinfo(title="Error",message="Could not allocate a socket for host machine")
        return
    
    index = lbox.curselection()
    try:
        alias = lbox.get(index)
    except:
        tkMessageBox.showinfo(title="Error",message="Not a valid server selection")
        return

    server = servers[alias]
    try:
        host.connect((server.addr, server.port))
    except socket.error:
        tkMessageBox.showinfo(title="Error",message="Could not connect to server")
        return

    doClient(host, server.serv_alias, server.my_alias)

def submit(entry_box, sock):
    msg = entry_box.get(1.0, "end")
    entry_box.delete(1.0, "end")
    sock.sendall(msg)

def logoff(w, host):
    try:
        host.shutdown(socket.SHUT_RDWR)
        host.close()
    except:
        host.close()
    w.destroy()

def doClient(host, serv_alias, my_alias):
    w = Toplevel(root)
    w.title(serv_alias)
    w.protocol("WM_DELETE_WINDOW", lambda: logoff(w, host))
    frame = ttk.Frame(w, padding=(0,0,4,4))

    #text boxes for received messages and message to be sent
    text_box = Text(frame, height=18, width=50, wrap="word")
    entry_box = Text(frame, height=4, width=50, wrap="word")

    #button to send message
    enter_but = ttk.Button(frame, text="Enter", command=lambda: submit(entry_box,host))
    exit_but = ttk.Button(frame, text="Exit", command=lambda: logoff(w, host))
    frame.bind("<Return>", lambda: submit(entry_box, host))

    #configure grid for text boxes and button
    frame.grid(column=0,row=0, sticky=(N,W,E,S))
    text_box.grid(column=0,row=0,padx=4,pady=4, sticky=(N,W,E,S))
    entry_box.grid(column=0,row=1,padx=4, sticky=(N,W,E,S))
    enter_but.grid(column=1,row=1, sticky=(E))
    exit_but.grid(column=1,row=2, sticky=(E))

    w.columnconfigure(0, weight=1)
    w.rowconfigure(0,weight=1)
    frame.columnconfigure("all", weight=1)
    frame.rowconfigure("all",weight=1)

    #set up to start actual work
    wt = workerThread(host, w, text_box)
    wt.start()
    host.sendall("\r\n")
    host.sendall(my_alias+"\n")

    
def setupHost(host_port):
    try:
        addr = socket.gethostbyname(socket.gethostname())
    except:
        print "Error retreiving IP address for host"
        return -2
    try:
        host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host.bind((addr, host_port))
        return host
    except:
        host.close()
        return -1
    

def main():
    global root
    
    root = Tk()
    root.title("Server Select")
    frame = ttk.Frame(root, padding=(12,12,0,12))
    ttk.Style().configure("TFrame", background="black")

    #hashmap of alias=>servers
    servers = {}

    serv = StringVar()

    #listbox of currently saved servers
    lbox = Listbox(frame, listvariable=servers.keys())
    scroll = ttk.Scrollbar(frame, orient=VERTICAL, command=lbox.yview)
    lbox['yscrollcommand'] = scroll.set

    #buttons to either create a server or select one
    nwsrv_but = ttk.Button(frame, text="New Server", command=lambda: newServer(servers, lbox))
    selsrv_but = ttk.Button(frame, text="Select", command=lambda: selectServer(servers, lbox))
    exit_but = ttk.Button(frame, text="Exit", command=lambda: root.destroy())

    #set up grid for GUI elements
    frame.grid(column=0, row=0, sticky=(N,W,E,S))
    lbox.grid(column=0, row=0, rowspan=10, sticky=(N,W,E,S))
    scroll.grid(column=1, row=0, rowspan=10, sticky=(N,W,E,S))
    nwsrv_but.grid(column=2, row=0, padx=4, sticky=(N,W,E,S))
    selsrv_but.grid(column=2, row=1, padx=4, sticky=(N,W,E,S))
    exit_but.grid(column=2, row=9, padx=4, sticky=(N,W,E,S))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure("all", weight=1)
    frame.rowconfigure("all", weight=1)

    root.mainloop()

main()
