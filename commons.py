#!/usr/bin/python3
# PyCraft common classes and methods

from utils import *; logstart('Commons')

class Updatable:
	def update(self, data={}, **kwdata): # TODO FIXME
		data.update(kwdata)
		self.__dict__.update(data)

if (__name__ == '__main__'): logstarted(); main()
else: logimported()

# by Sdore, 2018
