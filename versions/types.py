#!/usr/bin/python3
# PyCraft multiversioning data types

from ..protocol import *
from utils import S

Data = 'Data'
Bool = 'Bool'
Byte = 'Byte'
UByte = 'UByte'
Short = 'Short'
UShort = 'UShort'
Int = 'Int'
Long = 'Long'
Float = 'Float'
Double = 'Double'
UUID = 'UUID'
Angle = 'Angle'
String = 'String'
Chat = 'Chat'
Identifier = 'Identifier'
VarInt = 'VarInt'
VarLong = 'VarLong'

class Packet:
	def __init__(self, _state, _pid, **_fields):
		self.state, self.pid, self.fields = _state, _pid, _fields
	def __repr__(self):
		return f"<Packet state={self.state} pid={hex(self.pid)}>"
	def send(self, c, _protocol, **fields):
		return c.sendPacket(self, *(eval('write'+self.fields[i])(_protocol.__getattribute__(fields.get(i).name).value if (type(fields.get(i)) == Const) else fields.get(i)) for i in self.fields))
	def recv(self, c, _protocol):
		return S({i: eval('read'+self.fields[i])(c) for i in self.fields})
class Const:
	def __init__(self, value):
		self.value = value

# by Sdore, 2018
