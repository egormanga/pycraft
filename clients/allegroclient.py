#!/usr/bin/python3
# PyCraft allegro client

from Salleg import *
from pyglet.graphics import *
from utils.nolog import *; from utils import S as _S
from ..client import *
logstart('AllegroClient')

class App(ALApp):
	def load(self):

	def draw(self):
		pass

app = App()

@apmain
def main(cargs):
	app.run()

if (__name__ == '__main__'): main()
else: logimported()

# by Sdore, 2020
