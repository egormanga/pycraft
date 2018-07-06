#!/usr/bin/python3
# PyCraft protocol

import os, sys, time, zlib, base64, random, socket, struct, inspect
import config
from utils import *; logstart('Protocol')

PV = 340
compression = dict()

def begin(ip='', port=25565):
	global s
	s = socket.socket()
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((ip, port))
#	s.setblocking(False)
	s.listen()

def close():
	global s
	s.detach()
	del s

def sethandler(h): global handle; handle = h
def handle(c, a): # default handler
	l, pv = readPacketHeader(c)
	log(c.recv(l), raw=True)

def readN(c, t, n, name='', nolog=False):
	r = struct.unpack(t, c.recv(n))[0]
	if (not nolog):
		f = inspect.stack()[1][3][4:]
		f = f[0].lower() + f[1:] # flower! <3
		if (name): f += ' '+name
		log(2, "Reading %s: %s (%d)" % (f, hex(r), r))
	return r
def readBool(c, **kwargs): r = c.recv(1) == '\x01'; log(2, "Reading bool: %s" % r); return r
def readByte(c, **kwargs): return readN(c, 'B', 1, **kwargs)
def readUByte(c, **kwargs): return readN(c, 'b', 1, **kwargs)
def readShort(c, **kwargs): return readN(c, 'H', 2, **kwargs)
def readUShort(c, **kwargs): return readN(c, 'h', 2, **kwargs)
def readInt(c, **kwargs): return readN(c, 'i', 4, **kwargs)
def readLong(c, **kwargs): return readN(c, 'q', 8, **kwargs)
def readFloat(c, **kwargs): return readN(c, 'f', 4, **kwargs)
def readDouble(c, **kwargs): return readN(c, 'd', 8, **kwargs)

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

def readString(c, l=32767, name='', nolog=False):
	r = c.recv(min(readVarInt(c, nolog=True), l*4)).decode()
	if (not nolog):
		f = 'string'
		if (name): f += " '%s'" % name
		log(2, "Reading %s: \"%s\"" % (f, r))
	return r
def writeString(s): return writeVarInt(min(len(s), 32767)) + s.encode()

def readVarN(c, n, name='', nolog=False):
	i = int()
	r = int()
	try:
		b = -1
		while (b & 0b10000000):
			if (i > n): raise RuntimeError("%s is too big" % f)
			b = ord(c.recv(1))
			r |= (b & 0b01111111) << (7*i)
			i += 1
	except: pass
	if (not nolog):
		f = inspect.stack()[1][3][4:]
		f = f[0].lower() + f[1:] # a flower from Russia with love <3
		if (name): f += ' '+name
		log(2, "Reading %s: %s (%d)" % (f, hex(r), r))
	return r
def readVarInt(c, **kwargs): return readVarN(c, n=5, **kwargs)
def readVarLong(c, **kwargs): return readVarN(c, n=10, **kwargs)

def writeVarN(v, n): # FIXME: negative values
	i = int()
	r = bytes()
	try:
		while (v):
			if (i > n): raise RuntimeError("%s is too big" % f)
			t = v >> 7
			s = (v & 0b01111111) | (0b10000000 if (t) else 0)
			v = t
			r += s.to_bytes(1, 'big')
			i += 1
	except: pass
	return r or b'\x00'
def writeVarInt(v, **kwargs): return writeVarN(v, n=5, **kwargs)
def writeVarLong(v, **kwargs): return writeVarN(v, n=10, **kwargs)

def readPacketHeader(c):
	l = readVarInt(c, nolog=True)
	pid = readVarInt(c, nolog=True)
	log(2, "Reading packet header: length=%d, pid=%s" % (l, hex(pid)))
	return l, pid

def setCompression(a, threshold): global compression; compression[a] = threshold
def sendPacket(c, id, data, nolog=False):
	p = writeVarInt(id) + data
	l = len(p)
	a = c.getpeername()
	if (a in compression and -1 < compression[a] < l): p = writeVarInt(l) + zlib.compress(p); p = writeVarInt(len(p)) + p
	else: p = writeVarInt(l) + p
	r = c.send(p)
	log(2, "Sending packet: length=%d" % l)
	if (not nolog): log(2, p, raw=True)
	return r

def loop():
	try: handle(*s.accept())
	finally: log(2, '-'*os.get_terminal_size()[0], raw=True)

if (__name__ == '__main__'):
	logstarted()
	setlogfile('protocol.log')
	setloglevel(2)
	try: begin(ip=config.server_ip, port=config.server_port)
	except Exception as ex: exit(ex)
	while (True):
		try: loop()
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt: close(); exit()
else: logimported()

# by Sdore, 2018
