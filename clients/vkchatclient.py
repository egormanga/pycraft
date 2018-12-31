#!/usr/bin/python3
# PyCraft VK.com chat client

from ..client import *
from api import *
from .config import chat_id, password
from utils import *; logstart('VKChatClient')

setlogfile('PyCraft_chatclient.log')
db.setfile('vkchatclient.db')
tokens.require('access_token', 'messages,offline')

def main(ip, port=25565, name=config.default_username):
	global client
	db.load()
	setonsignals(exit)
	exceptions = queue.Queue()
	lp(eq=exceptions)
	client = MCClient(name=name)
	client.connect(ip, port)
	client.login()
	while (True):
		try:
			try: ex = exceptions.get()
			except queue.Empty: pass
			except TypeError: raise KeyboardInterrupt()
			else: raise ex
		except Exception as ex: exception(ex)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

#@MCClient.handler(0x0E, PLAY) # Chat Message
def handleChatMessage(s):
	c = readChat(s)
	if ('/l' in repr(c)): s.sendChatMessage('/l '+password)
	elif ('/tpaccept' in repr(c)): s.sendChatMessage('/tpaccept')
	#else: plog(c)

@proc
def loop():
	client.handle()

@handler
def handle(u):
	if (u[0] == 4):
		peer_id, body = u[3], u[5]
		if (peer_id != 2000000000+chat_id): return
		m = message(u[1], nolog=True)['items'][0]
		u = user(m['from_id'], groups=True)[0]
		if (m['text']): client.sendChatMessage(f"!{u['name']}: {format_message(m)}") # '/me | '

if (__name__ == '__main__'):
	argparser.add_argument('ip', metavar='<ip>')
	argparser.add_argument('port', nargs='?', default=25565)
	argparser.add_argument('-name', metavar='username', nargs='?', default=config.default_username)
	cargs = argparser.parse_args()
	logstarted(); main(cargs.ip, int(cargs.port), cargs.name)
else: logimported()

# by Sdore, 2018
