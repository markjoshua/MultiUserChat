from Tkinter import *
import tkMessageBox
import ttk
import socket
import threading
import select
import sys

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
                try:
                    if fd == self.sock.fileno():
                        line = recv_line(self.sock)
                        if line == "":
                            running = False
                        else:
                            self.text_box.config(state="normal")
                            self.text_box.insert("end", line)
                            self.text_box.config(state="disabled")
                except:
                    running = False
        if self.window:
            self.window.destroy()



#Class to manage the GUI aspect of preferences
class PreferenceWindow:
    def __init__(self, parent):
        self.parent = parent
        self.w = Toplevel(self.parent.parent)
        self.w.title("Preferences")
        
        self.frame = ttk.Frame(self.w, padding=(12,12,12,12))

        self.save_var = IntVar()
        self.save_srvs = Checkbutton(self.frame, text="Save Servers", variable=self.save_var, command=self.saveServers)
        if self.parent.preferences["saveservers"] == "true":
            self.save_srvs.select()
        self.close_but = ttk.Button(self.frame, text="Close", command=self.close)

        self.frame.grid(column=0,row=0, sticky=(N,W,E,S))
        self.save_srvs.grid(column=0,row=0, padx=4, pady=4, sticky=(N,W,E,S))
        self.close_but.grid(column=0,row=1, padx=4, pady=4, sticky=(N,W,E,S))

        self.w.columnconfigure("all", weight=1)
        self.w.rowconfigure("all", weight=1)
        self.frame.columnconfigure("all", weight=1)
        self.frame.rowconfigure("all", weight=1)


        #Handles the save server preference. The code to write server list
        #out to disk is also called in chatClient if the preference is set
        #to true.
    def saveServers(self):
        if(self.save_var.get()):
            self.parent.preferences["saveservers"] = "true"
            f = open("servers", "w")
            serv_map = self.parent.servers
            for i in serv_map:
                line = serv_map[i].addr+" "+str(serv_map[i].port)+" "+serv_map[i].my_alias+" "+serv_map[i].serv_alias
                f.write(line)
            f.close()
        else:
            self.parent.preferences["saveservers"] = "false"        


        #Upon closing the preference window, the pref file is updated
    def close(self):
        f = open("prefs", "w")
        for key in self.parent.preferences:
            line = key + " " + self.parent.preferences[key]+"\n"
            f.write(line)
        f.close()
        self.w.destroy()
        


#handles receiving and sending aspects as well as the GUI for
#chat window
class Client:
    def __init__(self, parent, host, serv_alias, my_alias):
        self.w = Toplevel(parent.parent)
        self.w.title(serv_alias)
        self.w.protocol("WM_DELETE_WINDOW", self.logoff)
        self.w.bind("<Return>", lambda event: self.submit(event))

        self.host = host
        
        self.frame = ttk.Frame(self.w, padding=(0,0,4,4))

        #text boxes for received messages and message to be sent
        self.text_box = Text(self.frame, height=18, width=50, wrap="word")
        self.entry_box = Text(self.frame, height=4, width=50, wrap="word")

        #button to send message
        self.enter_but = ttk.Button(self.frame, text="Enter", command=lambda: self.submit(0))
        self.exit_but = ttk.Button(self.frame, text="Exit", command=self.logoff)
        
        #configure grid for text boxes and button
        self.frame.grid(column=0,row=0, sticky=(N,W,E,S))
        self.text_box.grid(column=0,row=0,padx=4,pady=4, sticky=(N,W,E,S))
        self.entry_box.grid(column=0,row=1,padx=4, sticky=(N,W,E,S))
        self.enter_but.grid(column=1,row=1, sticky=(E))
        self.exit_but.grid(column=1,row=2, sticky=(E))

        self.w.columnconfigure("all", weight=1)
        self.w.rowconfigure("all",weight=1)
        self.frame.columnconfigure("all", weight=1)
        self.frame.rowconfigure("all",weight=1)

        #spawn thread to read input from server to screen
        #Then initialize log on protocol with server by sending
        # CRLF followed by your alias
        self.wt = workerThread(self.host, self.w, self.text_box)
        self.wt.start()
        self.host.sendall("\r\n")
        self.host.sendall(my_alias+"\n")


    #wrapper for submitting all contents of a text box
    #and then clearing the box
    def submit(self, event):
        msg = self.entry_box.get(1.0, "end")
        if event:
            msg = msg[:len(msg)-1]
        self.entry_box.delete(1.0, "end")
        self.host.sendall(msg)


    #wrapper for peacefully logging off server
    def logoff(self):
        try:
            self.host.shutdown(socket.SHUT_RDWR)
            self.host.close()
        except:
            self.host.close()
        self.w.destroy()



class chatClient:
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("Server Select")
        self.parent.protocol("WM_DELETE_WINDOW", self.exit_prog)

        self.frame = ttk.Frame(self.parent, padding=(12,12,0,12))
        #ttk.Style().configure("TFrame", background="black")

        #dictionary that holds Server objects by alias
        self.servers = {}

        #open client window and socket pairs
        self.windows = []

        #set up the menu
        self.menu = self.setUpMenu()

        #GUI display of self.servers in the form of a listbox
        self.lbox = Listbox(self.frame, listvariable=self.servers.keys())
        self.scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.lbox.yview)
        self.lbox["yscrollcommand"] = self.scroll.set

        #preferences
        self.preferences = {}
        self.loadPreferences()
        self.handlePreferences()

        #create buttons
        self.nwsrv_but = ttk.Button(self.frame, text="New Server", command=self.newServer)
        self.remsrv_but = ttk.Button(self.frame, text="Remove Server", command=self.removeServer)
        self.selsrv_but = ttk.Button(self.frame, text="Select Server", command=self.selectServer)
        self.exit_but = ttk.Button(self.frame, text="Exit", command=self.exit_prog)

        #set up grid for GUI elements
        self.frame.grid(column=0, row=0, columnspan=2, rowspan=15, sticky=(N,W,E,S))
        self.lbox.grid(column=0, row=0, rowspan=15, sticky=(N,W,E,S))
        self.scroll.grid(column=1, row=0, rowspan=15, sticky=(N,W,E,S))
        self.nwsrv_but.grid(column=2, row=0, padx=4, sticky=(N,W,E,S))
        self.remsrv_but.grid(column=2, row=1, padx=4, sticky=(N,W,E,S))
        self.selsrv_but.grid(column=2, row=7, padx=4, sticky=(N,W,E,S))
        self.exit_but.grid(column=2, row=13, padx=4, sticky=(N,W,E,S))

        self.parent.columnconfigure("all", weight=1)
        self.parent.rowconfigure("all", weight=1)
        self.frame.columnconfigure("all", weight=1)
        self.frame.rowconfigure("all", weight=1)


        #if you have saved preferences this will load them.
    def loadPreferences(self):
        try:
            f = open("prefs", "r")
            pref_lines = f.readlines()
            for i in pref_lines:
                option = i.split()[0]
                value = i.split()[1]
                self.preferences[option] = value
            f.close()
        except:
            print "No preference file found"


        #handles any loaded preferences
    def handlePreferences(self):
        if "saveservers" in self.preferences:
            if self.preferences["saveservers"] == "true":
                f = open("servers", "r")
                serv_list = f.readlines()
                for i in serv_list:
                    serv_info = i.split()
                    self.addServer(0, serv_info[0], serv_info[1], serv_info[2], serv_info[3])


        #helper function to write server list out to disk
    def writeServers(self):
        f = open("servers", "w")
        serv_map = self.servers
        for i in serv_map:
            line = serv_map[i].addr+" "+str(serv_map[i].port)+" "+serv_map[i].my_alias+" "+serv_map[i].serv_alias
            f.write(line)
        f.close()           


        #set up menu bar for chatClient
    def setUpMenu(self):
        menubar = Menu(self.parent)
        #menubar.configure()
        menu_file = Menu(menubar)
        #menu_file.configure()
        menu_edit = Menu(menubar)
        #menu_edit.configure()
        self.parent["menu"] = menubar
        menubar.add_cascade(menu=menu_file, label="File")
        menubar.add_cascade(menu=menu_edit, label="Edit")

        menu_file.add_command(label="Exit", command=self.exit_prog)

        menu_edit.add_command(label="Preferences", command=self.openPreferences)

        return menubar


        #creates a PreferenceWindow class that handles
        #GUI and preference selection
    def openPreferences(self):
        p = PreferenceWindow(self)
        

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
                        if "saveservers" in self.preferences:
                            if self.preferences["saveservers"] == "true":
                                self.writeServers()
                        if window:
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
                        if "saveservers" in self.preferences:
                            if self.preferences["saveservers"] == "true":
                                self.writeServers()
                        if window:
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
        c = Client(self, host, serv_alias, my_alias)
        self.windows.append(c)


    #wrapper for peacefully exiting the program
    def exit_prog(self):
        for i in self.windows:
            i.logoff()
        self.parent.quit()
        self.parent.destroy()


if __name__=="__main__":
    root = Tk()
    new_client = chatClient(root)
    root.mainloop()
