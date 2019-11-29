#!/usr/bin/python3
# PyCraft chat client

from utils.nolog import *
from ..client import *
logstart('ChatClient')

setlogfile('PyCraft_chatclient.log')

class ChatClient(MCClient):
	handlers = Handlers(MCClient.handlers)

@apmain
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-name', metavar='username', default=ClientConfig.username)
def main(cargs):
	class config(ClientConfig):
		username = cargs.name

	client = Builder(ChatClient, config=config) \
		.connect((cargs.ip, cargs.port)) \
		.login() \
		.block(state=PLAY) \
		.build()

	S.ChatMessage.send(client,
		message = "/kill",
	)

	while (True):
		try:
			client.handle()
			if (not select.select((sys.stdin,), (), (), 0)[0]): continue
			try: msg = input().strip()
			except EOFError: break
			if (not msg): continue
			S.ChatMessage.send(client,
				message = msg,
			)
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

@ChatClient.handler(C.ChatMessage)
def handleChatMessage(s, p):
	log('\033[0m'+formatChat(p.message, ansi=True), ll='[\033[0mChat\033[0;96m]')

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
