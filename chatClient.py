from Tkinter import *
import tkMessageBox
import ttk
import socket
import threading
import select
import sys

#Holds information important for connecting to servers
class Server:
    def __init__(self, addr="", port=6666, my_alias="Anon", serv_alias=None):
        self.addr = addr
        self.port = port
        self.my_alias = my_alias
        if serv_alias is None:
            self.serv_alias = addr
        else:
            self.serv_alias = serv_alias

#Worker thread that reads input from a socket and displays it in a text box
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
            

class chatClient:
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("Server Select")
        self.parent.protocol("WM_DELETE_WINDOW", self.exit_prog)

        self.frame = ttk.Frame(self.parent, padding=(12,12,0,12))
        #ttk.Style().configure("TFrame", background="black")

        #dictionary that holds Server objects by alias
        self.servers = {}

        #GUI display of self.servers in the form of a listbox
        self.lbox = Listbox(self.frame, listvariable=self.servers.keys())
        self.scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.lbox.yview)
        self.lbox["yscrollcommand"] = self.scroll.set

        #create buttons
        self.nwsrv_but = ttk.Button(self.frame, text="New Server", command=self.newServer)
        self.remsrv_but = ttk.Button(self.frame, text="Remove Server", command=self.removeServer)
        self.selsrv_but = ttk.Button(self.frame, text="Select Server", command=self.selectServer)
        self.exit_but = ttk.Button(self.frame, text="Exit", command=self.exit_prog)

        #set up grid for GUI elements
        self.frame.grid(column=0, row=0, columnspan=2, rowspan=10, sticky=(N,W,E,S))
        self.lbox.grid(column=0, row=0, rowspan=10, sticky=(N,W,E,S))
        self.scroll.grid(column=1, row=0, rowspan=10, sticky=(N,W,E,S))
        self.nwsrv_but.grid(column=2, row=0, padx=4, sticky=(N,W,E,S))
        self.remsrv_but.grid(column=2, row=1, padx=4, sticky=(N,W,E,S))
        self.selsrv_but.grid(column=2, row=3, padx=4, sticky=(N,W,E,S))
        self.exit_but.grid(column=2, row=6, padx=4, sticky=(N,W,E,S))

        self.parent.columnconfigure("all", weight=1)
        self.parent.rowconfigure("all", weight=1)
        self.frame.columnconfigure("all", weight=1)
        self.frame.rowconfigure("all", weight=1)


    def newServer(self):
        #create new window for server info input
        w = Toplevel(self.parent)
        w.title("Add Server")
        frame = ttk.Frame(w, padding=(12,12,0,0))

        add_lbl = ttk.Label(frame, text="Enter address:")
        prt_lbl = ttk.Label(frame, text="Enter port number:")
        my_alias_lbl = ttk.Label(frame, text="Enter your alias(username):")
        serv_alias_lbl = ttk.Label(frame, text="Enter an alias for the server:")

        add_entry = ttk.Entry(frame)
        prt_entry = ttk.Entry(frame)
        my_alias_entry = ttk.Entry(frame)
        serv_alias_entry = ttk.Entry(frame)

        accept_but = ttk.Button(frame, text="Accept", command=lambda:
                                self.addServer(w, add_entry.get(), prt_entry.get(),
                                          my_alias_entry.get(), serv_alias_entry.get()))
        cancel_but = ttk.Button(frame, text="Cancel", command=w.destroy)
        w.bind("<Return>", lambda event: self.addServer(w, add_entry.get(), prt_entry.get(),
                                                        my_alias_entry.get(), serv_alias_entry.get()))

        frame.grid(column=0, row=0, columnspan=1, rowspan=9, sticky=(N,W,E,S))
        add_lbl.grid(column=0, row=0, sticky=(N,W,E,S))
        add_entry.grid(column=0, row=1, sticky=(N,W,E,S))
        prt_lbl.grid(column=0, row=2, sticky=(N,W,E,S))
        prt_entry.grid(column=0, row=3, sticky=(N,W,E,S))
        my_alias_lbl.grid(column=0, row=4, sticky=(N,W,E,S))
        my_alias_entry.grid(column=0, row=5, sticky=(N,W,E,S))
        serv_alias_lbl.grid(column=0, row=6, sticky=(N,W,E,S))
        serv_alias_entry.grid(column=0, row=7, sticky=(N,W,E,S))
        accept_but.grid(column=1, row=8, padx=12, pady=12, sticky=(N,W,E,S))
        cancel_but.grid(column=1, row=9, padx=12, pady=12, sticky=(N,W,E,S))

        w.columnconfigure("all", weight=1)
        w.rowconfigure("all", weight=1)
        frame.columnconfigure("all", weight=1)
        frame.rowconfigure("all", weight=1)

        #Insert optional into serv_alias entry box to let
        #user know this field is optional
        serv_alias_entry.delete(0, "end")
        serv_alias_entry.insert(0, "Optional")


    #This method actually attempts to add the inputted server to
    #the dictionary and listbox. Does some error checking to ensure
    #important fields (port, alias, etc.) are correct
    def addServer(self, window, addr, port, my_alias, serv_alias):
        if port == "":
            tkMessageBox.showinfo(title="Error", message="Must enter a port number")
        elif my_alias == "":
            tkMessageBox.showinfo(title="Error", message="Must enter an alias(username)")
        else:
            if serv_alias != "Optional":
                if serv_alias in self.servers:
                    tkMessageBox.showinfo(title="Error", message="Server alias already in use")
                else:
                    try:
                        new_serv = Server(addr, int(port), my_alias, serv_alias)
                        self.servers[serv_alias] = new_serv
                        self.lbox.insert("end", serv_alias)
                        window.destroy()
                    except:
                        tkMessageBox.showinfo(title="Error", message="One or more of the entered fields is incorrect")
            else:
                if addr in self.servers:
                    tkMessageBox.showinfo(title="Error", message="Server alias already in use")
                else:
                    try:
                        new_serv = Server(addr, int(port), my_alias)
                        self.servers[addr] = new_serv
                        self.lbox.insert("end", addr)
                        window.destroy()
                    except:
                        tkMessageBox.showinfo(title="Error", message="One or more of the entered fields is incorrect")


    def removeServer(self):
        index = self.lbox.curselection()
        try:
            serv_alias = self.lbox.get(index)
        except:
            tkMessageBox.showinfo(title="Error", message="Not a valid server selection")
            return

        self.servers.pop(serv_alias)
        self.lbox.delete(index)
        
    #sets up a socket on the host side between 5000 and 6000.
    #Then attempt to connect to selected server. On success,
    #doClient handles the rest of the work.
    def selectServer(self):
        host_port = 5000
        host = self.setUpHost(host_port)
        count = 0
        while host == -1 and count < 1000:
            host_port += 1
            host = self.setUpHost(host_port)
        if count == 1000:
            tkMessageBox.showinfo(title="Error", message="Could not allocate socket for host machine")
            return

        index = self.lbox.curselection()
        try:
            serv_alias = self.lbox.get(index)
        except:
            tkMessageBox.showinfo(title="Error", message="Not a valid server selection")

        server = self.servers[serv_alias]
        try:
            host.connect((server.addr, server.port))
        except socket.error:
            tkMessageBox.showinfo(title="Error", message="Could not connect to server")
            return

        self.doClient(host, server.serv_alias, server.my_alias)


    #Wrapper for setting up a socket with port number host_port
    #at the IP address of the host
    def setUpHost(self, host_port):
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

    #Create a new window for chatting. Messages are entered into a
    #text box, input is displayed on a separate text box handled by
    #a separate thread.
    def doClient(self, host, serv_alias, my_alias):
        w = Toplevel(self.parent)
        w.title(serv_alias)
        w.protocol("WM_DELETE_WINDOW", lambda: self.logoff(w, host))
        frame = ttk.Frame(w, padding=(0,0,4,4))

        #text boxes for received messages and message to be sent
        text_box = Text(frame, height=18, width=50, wrap="word")
        entry_box = Text(frame, height=4, width=50, wrap="word")

        #button to send message
        enter_but = ttk.Button(frame, text="Enter", command=lambda: self.submit(entry_box,host))
        exit_but = ttk.Button(frame, text="Exit", command=lambda: self.logoff(w, host))
        w.bind("<Return>", lambda event: self.submit(entry_box, host))

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

        #spawn thread to read input from server to screen
        #Then initialize log on protocol with server by sending
        # CRLF followed by your alias
        wt = workerThread(host, w, text_box)
        wt.start()
        host.sendall("\r\n")
        host.sendall(my_alias+"\n")

    #wrapper for submitting all contents of a text box
    #and then clearing the box
    def submit(self, entry_box, sock):
        msg = entry_box.get(1.0, "end")
        entry_box.delete(1.0, "end")
        sock.sendall(msg)

    #wrapper for peacefully logging off server
    def logoff(self, w, host):
        try:
            host.shutdown(socket.SHUT_RDWR)
            host.close()
        except:
            host.close()
        w.destroy()

    #wrapper for peacefully exiting the program
    def exit_prog(self):
        self.parent.quit()
        self.parent.destroy()


if __name__=="__main__":
    root = Tk()
    new_client = chatClient(root)
    root.mainloop()
