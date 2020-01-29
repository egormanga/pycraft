#!/usr/bin/python3
# PyCraft VK.com chat client

from api import *
from utils.nolog import *
from ..client import *
logstart('VKChatClient')

setlogfile('PyCraft_vkchatclient.log')
db.setfile('PyCraft_vkchatclient.db')
API.mode = 'group'
tokens.require('access_token', group_scope_all)

class VKChatClient(MCClient):
	handlers = Handlers(MCClient.handlers)

@VKChatClient.handler(C.ChatMessage)
def handleChatMessage(s, p):
	log('\033[0m'+formatChat(p.message, ansi=True), ll='[\033[0mChat\033[0;96m]')
	if (p.message.get('translate') == 'chat.type.announcement' and p.message['with'][0] != client.config.username): send(2000000000+chat_id, formatChat(p.message))

@apmain
@aparg('group_id', metavar='<group_id>')
@aparg('chat_id', metavar='<chat_id>', type=int)
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-name', metavar='username', default='VK')
def main(cargs):
	global client, chat_id, longpoll

	group.id = groups(cargs.group_id, access_token=service_key)[0]['id']
	chat_id = cargs.chat_id

	db.load()
	setonsignals(exit)
	exceptions = queue.Queue()
	longpoll = lp(eq=exceptions)

	class config(ClientConfig):
		username = cargs.name

	try:
		client = Builder(VKChatClient, config=config) \
			.connect((cargs.ip, cargs.port)) \
			.login() \
			.block(state=PLAY) \
			.build()

		S.ChatMessage.send(client,
			message = "/kill",
		)
	except NoServer as ex: exit(ex)

	while (True):
		try:
			client.handle()
			try: ex = exceptions.get(timeout=0.01)
			except queue.Empty: pass
			except TypeError: raise KeyboardInterrupt()
			else: raise ex
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

@command_unknown
def c_unknown():
	if (peer_id != 2000000000+chat_id): return
	if (not text): return
	u = user(from_id, groups=True, nolog=True)[0]
	S.ChatMessage.send(client,
		message = f"/say {u['name']}: {format_message(m)}",
	)

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
