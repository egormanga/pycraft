#!/usr/bin/python3
# pycraft

from protocol import *
from server import *
from utils import *; logstart('pycraft')

def main():
	server = MCServer()
	server.start()
	server.loop()

if (__name__ == '__main__'): logstarted(); main()
else: logimported()

# by Sdore, 2018
