#!/usr/bin/python3
# PyCraft console client
# [OUTDATED]

import cimg, curses, curses.textpad
from pycraft.protocol import *
from utils import *; logstart('Client')

def draw_map(stdscr, map, pos):
	h, w = stdscr.getmaxyx()
	for y in range(pos[1]-h//2, pos[1]+h//2):
		for x in range(pos[0]-w//2, pos[0]+w//2):
			try: stdscr.addch(y, x, map[x][y])
			except: stdscr.addch(y, x, '?')

def textbox(stdscr, y, x, h, w, name=str(), textColor=int(), frameColor=int(), value=str()):
	if (name): name += ' '
	stdscr.addstr(y, x, name, curses.color_pair(textColor))
	nw = curses.newwin(h, w-len(name), y, x+len(name))
	#stdscr.addstr(y, x+len(name), value)
	nw.addstr(0, 0, value)
	tb = curses.textpad.Textbox(nw)

	stdscr.attron(frameColor)
	curses.textpad.rectangle(stdscr, y-1, x-1+len(name), y+h, x+w)
	stdscr.attroff(frameColor)

	stdscr.refresh()
	return tb

def main(stdscr):
	stdscr.keypad(True)
	curses.noecho()
	curses.curs_set(False)
	stdscr.nodelay(True)
	curses.init_pair(curses.COLOR_RED, curses.COLOR_RED, curses.COLOR_BLACK)

	s = socket.socket()
	state = int()
	errors = list()
	map = [[]]

	while (True):
		try:
			h, w = stdscr.getmaxyx()
			if (state == 0):
				stdscr.addstr(0	, w//2-3, "PyCraft")
				stdscr.addstr(1, w//2-2, "v0.1")
				stdscr.addstr(2, 0, '─'*w)
				ip = textbox(stdscr, 4, 2, 1, w-4, "IP: ", 'ip' in errors, value='serv')
				port = textbox(stdscr, 7, 2, 1, w-4, "Port: ", 'port' in errors, value='25567')
				ip = ip.edit().strip(); port = port.edit().strip()
				try: port = int(port); assert port < 65536
				except: port = int()
				errors = list()
				if (not ip): errors.append('ip')
				if (not port): errors.append('port')
				s = socket.socket()
				try: s.connect((ip, port)); state = 1
				except OSError as ex: stdscr.addstr(9, 2, str(ex), curses.color_pair(curses.COLOR_RED))
			elif (state == 1):
				sendPacket(s, 0x00, # Handshake
					writeVarInt(PV) + # Protocol Version
					writeString(ip) + # Server Address
					writeUShort(port) + # Server Port
					writeVarInt(state) # Next State
				)
				sendPacket(s, 0x00) # Request
				readPacketHeader(s) # Response
				try: data = json.loads(readString(s, 32767, nolog=True))
				except Exception as ex: data = {'version': {'name': '?'}, 'description': {'text': "Error: %s" % ex}, 'players': {'max': '?', 'online': '?', 'sample': [{'name': '?'}]}}
				nw = curses.newwin(10, w-4, 9, 2); nw.immedok(True)
				if (data.get('favicon')): nw.addstr(1, 1, cimg.ascii(cimg.Image.open(io.BytesIO(base64.b64decode(data['favicon'][len('data:image/png;base64,'):]))), 8, '░▒▓█', padding=1))
				nw.addstr(1, 10, "%s @ %s" % (data['description']['text'], data['version']['name']))
				nw.addstr(2, 10, "Players (%s/%s):" % tuple(Sdict(data['players'])@['online', 'max']))
				nw.addstr(3, 10, ', '.join(Slist(data['players']['sample'])@['name']))
				nw.box()
				nw2 = curses.newwin(1, 32, 20, 10); nw2.immedok(True)
				nw2.addstr(0, 0, "Enter to join, Esc to cancel.")
				stdscr.nodelay(False)
				ch = stdscr.getkey()
				stdscr.nodelay(True)
				if (ch == '\n'): state = 2
				elif (ch == '\033'): del nw, nw2; stdscr.touchwin(); s.close(); state = 0
			stdscr.refresh()
		except KeyboardInterrupt: break # clear; while true; do nc -l -p 8080; sleep 1; done
						# ./client.py -vvv 2> >(tcpconnect pc 8080)
						# while true; do clear; ./server.py -vvv; sleep 1; done

def keepAlive(s, pid):
	id = int(time.time())
	sendPacket(s, pid, writeLong(id)) # Ping
	return readPacketHeader(s) == pid and readLong(s) == id

if (__name__ == '__main__'):
	logstarted(); ll = str().join(sys.argv[1:]); setloglevel(ll.count('v')-ll.count('q'))
	try: curses.wrapper(main)
	except KeyboardInterrupt: exit()
else: logimported()

# by Sdore, 2019
