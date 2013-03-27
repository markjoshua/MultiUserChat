#MultiUserChat

A simple server and client for IRC-like multi user chat using Python 2.7.3 and Tkinter for the GUI.
Designed to run on Unix-based systmes so Windows users may have problems.  (Tkinter/python socket compatibility)
May be some compatibility issues (mainly print statements) with newer version of Python.

To run the server, the best way is by command line:

>python chatServer.py [OPTIONS]

options:
>--help        print out usage/help info

>-a ADDR       sets server to run on ADDR which should be an IPv4 address

>-p PORT       sets server to user port PORT for an address

>-b BKLG       sets the backlog limit for the server

All options are optional, the default address is localhost and the default port is 6666. Default backlog is 5.

The client is also easiest run through command line:

>python chatClient.py

The client brings up a GUI window allowing you to enter in new servers or select from existing ones.
Adding new servers require you to enter the server address (IPv4 dotted quad or name), the port number,
and your pseudonym(alias) for that server. The server can also optionally be allocated a user-side alias.


###TO DO:
>Possibly refactor chatServer.py

>Add more options to preferences. It currently only has a 'save servers' checkbutton

>Send images and files
