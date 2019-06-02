#!/usr/bin/python3
# PyCraft chat client

from ..client import *
from utils import *; logstart('ChatClient')

def main(ip, port=25565, name=config.default_username):
	setlogfile('PyCraft_chatclient.log')
	client = MCClient(name=name)
	client.connect(ip, port)
	client.login()
	while (True):
		try:
			client.handle()
			try: msg = select.select([sys.stdin], [], [], 0)[0][0].readline().strip()
			except IndexError: msg = ''
			if (msg):
				#client.login()
				#client.block(state=PLAY)
				client.sendChatMessage(msg)
				#client.leave()
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

#@MCClient.handler(0x0E, PLAY) # Chat Message
def handleChatMessage(s):
	c = readChat(s)
	try: log(' '.join(i['text'] if (type(i) == dict) else str(i) for i in c['with']))
	except: plog(c)

if (__name__ == '__main__'):
	argparser.add_argument('ip', metavar='<ip>')
	argparser.add_argument('port', nargs='?', default=25565)
	argparser.add_argument('-name', metavar='username', nargs='?', default=config.default_username)
	cargs = argparser.parse_args()
	logstarted(); main(cargs.ip, int(cargs.port), cargs.name)
else: logimported()

# by Sdore, 2019
