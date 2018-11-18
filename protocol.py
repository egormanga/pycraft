#!/usr/bin/python3
# PyCraft Minecraft protocol

import uuid, ctypes, struct, inspect
from utils import *; logstart('Protocol')

PV = 404

class State(int):
	def __repr__(self): return f"<state {str(self)} ({int(self)})>"
	def __str__(self): return ('ALL/NONE', 'HANDSHAKING', 'STATUS', 'LOGIN', 'PLAY')[self+1]
	def setstate(self, s): self = State(s); log(1, f"New state: {str(self)}")
ALL, HANDSHAKING, STATUS, LOGIN, PLAY = map(State, range(-1, 4)) # States

def read(c, n=int(), nolog=False):
	r = c.read(n)
	if (not nolog): log(3, f"Reading bytes: {r}")
	return r
def readN(c, t, name='', nolog=False):
	r = struct.unpack(t, read(c, struct.calcsize(t), nolog=True))[0]
	if (not nolog):
		f = inspect.stack()[1][3][4:]
		if (f == 'UUID'): log(3, f"Reading {f}: {uuid.UUID(int=r)}")
		else: log(3, f"""Reading {f}{" '"+name+"'" if (name) else ''}: {hex(r) if (type(r) != float) else float.hex(r)} ({r})""")
	return r
def readBool(c, **kwargs): r = c.read(1) != b'\0'; log(3, f"Reading bool: {r}"); return r
def readByte(c, **kwargs): return readN(c, 'B', **kwargs)
def readUByte(c, **kwargs): return readN(c, 'b', **kwargs)
def readShort(c, **kwargs): return readN(c, 'H', **kwargs)
def readUShort(c, **kwargs): return readN(c, 'h', **kwargs)
def readInt(c, **kwargs): return readN(c, 'i', **kwargs)
def readLong(c, **kwargs): return readN(c, 'q', **kwargs)
def readFloat(c, **kwargs): return readN(c, 'f', **kwargs)
def readDouble(c, **kwargs): return readN(c, 'd', **kwargs)
def readUUID(c, **kwargs): return readN(c, '>QQ', **kwargs)
def readAngle(c, **kwargs): return readN(c, 'b', **kwargs)
def readString(c, l=32767, name='', nolog=False):
	r = c.read(min(readVarInt(c, nolog=True), l*4)).decode()
	if (not nolog): log(3, f"""Reading string{" '"+name+"'" if (name) else ''}: "{r}\"""")
	return r
def readIdentifier(c, **kwargs):
	return readString(c, **kwargs).split(':', maxsplit=1)

def writeN(t, *v): return struct.pack(t, *v)
def writeBool(v): return bytes([v])
def writeByte(v): return writeN('B', v)
def writeUByte(v): return writeN('b', v)
def writeShort(v): return writeN('H', v)
def writeUShort(v): return writeN('h', v)
def writeInt(v): return writeN('i', v)
def writeLong(v): return writeN('q', v)
def writeFloat(v): return writeN('f', v)
def writeDouble(v): return writeN('d', v)
def writeUUID(v): return writeN('>QQ', (v.int >> 64) & 2**64-1, v.int & 2**64-1)
def writePosition(x, y, z, *v): return writeN('q', ((x % 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF))
def writeString(s, l=0): return writeVarInt(min(len(s), l) if (l) else len(s)) + (s.encode()[:l] if (l) else s.encode())
def writeIdentifier(ns, v): return writeString(f"{ns}:{v}")

def readVarN(c, n, name='', nolog=False):
	r = int()
	i = int()
	f = inspect.stack()[1][3][4:]
	for i in range(n):
		b = (c.read(1) or b'\0')[0]
		r |= (b & (1 << 7)-1) << (7*i)
		if (not b & (1 << 7)): break
	else: raise \
		ValueError(f"{f} is too big")
	if (not nolog): log(3, f"Reading {(f+' '+name).strip()}: {hex(r)} ({r})")
	return r
def readVarInt(c, **kwargs): return ctypes.c_int(readVarN(c, n=5, **kwargs)).value
def readVarLong(c, **kwargs): return ctypes.c_long(readVarN(c, n=10, **kwargs)).value

def writeVarN(v):
	r = bytearray()
	while (True):
		c = v & (1 << 7)-1
		v >>= 7
		if (v): c |= (1 << 7)
		r.append(c)
		if (not v): break
	return bytes(r)
def writeVarInt(v): return writeVarN(ctypes.c_uint(v).value)
def writeVarLong(v): return writeVarN(ctypes.c_ulong(v).value)

if (__name__ == '__main__'): logstarted(); exit()
else: logimported()

# by Sdore, 2018
