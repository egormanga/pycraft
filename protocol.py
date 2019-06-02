#!/usr/bin/python3
# PyCraft Minecraft protocol

import json, ctypes, struct, inspect, builtins
from uuid import *
from utils import constrain

def hex(x, l=2): return '0x%%0%dX' % l % x

class State(int):
	def __repr__(self): return f"<state {str(self)} ({int(self)})>"
	def __str__(self): return ('NONE', 'HANDSHAKING', 'STATUS', 'LOGIN', 'PLAY')[self+1]
	def __bool__(self): return self != -1
HANDSHAKING, STATUS, LOGIN, PLAY = map(State, range(4)) # States

def readN(c, t): return struct.unpack(t, c.read(struct.calcsize(t)))[0]
def readBool(c): return (False, True)[c.read(1)[0]]
def readByte(c): return readN(c, 'B')
def readUByte(c): return readN(c, 'b')
def readShort(c): return readN(c, 'H')
def readUShort(c): return readN(c, 'h')
def readInt(c): return readN(c, 'i')
def readLong(c): return readN(c, 'q')
def readFloat(c): return readN(c, 'f')
def readDouble(c): return readN(c, 'd')
def readUUID(c): return readN(c, '>QQ')
def readAngle(c): return readN(c, 'b')
def readString(c, l=32767): return c.read(min(readVarInt(c), l*4)).decode()
def readChat(c): return json.loads(readString(c))
def readIdentifier(c): return readString(c).split(':', maxsplit=1)

def writeN(t, *v): return struct.pack(t, *((int if (t not in 'fd') else float)(i or 0) for i in v))
def writeBool(v): return bytes((bool(v),))
def writeByte(v): return writeN('B', v)
def writeUByte(v): return writeN('b', v)
def writeShort(v): return writeN('H', v)
def writeUShort(v): return writeN('h', v)
def writeInt(v): return writeN('i', v)
def writeLong(v): return writeN('q', v)
def writeFloat(v): return writeN('f', v)
def writeDouble(v): return writeN('d', v)
def writeUUID(v): return writeN('>QQ', (v.int >> 64) & 2**64-1, v.int & 2**64-1)
def writePosition(pos): return writeN('q', ((int(pos.x) % 0x3FFFFFF) << 38) | ((int(pos.y) & 0xFFF) << 26) | (int(pos.z) & 0x3FFFFFF))
def writeString(s, l=0): s = s[:constrain(l, 0, 32767)].encode('utf-8') if (s is not None) else b''; return writeVarInt(len(s)) + s
def writeChat(c): return json.dumps(c, ensure_ascii=False)
def writeIdentifier(ns, v): return writeString(':'.join((ns, v)))
def writeData(v): return v

def readVarN(c, n):
	r = int()
	i = int()
	for i in range(n):
		b = (c.read(1) or b'\0')[0]
		r |= (b & (1 << 7)-1) << (7*i)
		if (not b & (1 << 7)): break
	else: raise \
		ValueError(f"{inspect.stack()[1][3][4:]} is too big")
	return r
def readVarInt(c): return ctypes.c_int(readVarN(c, 5)).value
def readVarLong(c): return ctypes.c_long(readVarN(c, 10)).value

def writeVarN(v):
	r = bytearray()
	while (True):
		c = v & (1 << 7)-1
		v >>= 7
		if (v): c |= (1 << 7)
		r.append(c)
		if (not v): break
	return bytes(r)
def writeVarInt(v): return writeVarN(ctypes.c_uint(v or 0).value)
def writeVarLong(v): return writeVarN(ctypes.c_ulong(v or 0).value)

# by Sdore, 2019
