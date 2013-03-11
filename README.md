MultiUserChat
-------------

A simple server and client for IRC-like multi user chat using Python and Tkinter for the GUI.
Designed to run on Unix-based systmes so Windows users may have problems.  (Tkinter/python socket compatibility)

To run the server, the best way is by command line:

python chatServer.py [OPTIONS]

options:
--help        print out usage/help info
-a ADDR       sets server to run on ADDR which should be an IPv4 address
-p PORT       sets server to user port PORT for an address
-b BKLG       sets the backlog limit for the server

All options are optional, the default address is localhost and the default port is 6666. Default backlog is 5.

The client is also easiest run through command line:

python tkintertest.py

