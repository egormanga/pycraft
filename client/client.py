#!/usr/bin/python3
# PyCraft console client

from math import *
from utils import *; logstart('Client')

def main():
	pass

if (__name__ == '__main__'): logstarted(); ll = str().join(sys.argv[1:]); setloglevel(ll.count('v')-ll.count('q')); main()
else: logimported()

# by Sdore, 2018
