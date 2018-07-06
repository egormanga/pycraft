#!/usr/bin/python3
# PyCraft server

import json
from pycraft.protocol import *
from pynbt import *
from uuid import *
from utils import *; logstart('Server')

setlogfile('server.log')
players = {
	'ip1': {
		'name': "GateheaD",
		'uuid': UUID("a9145967-a36b-4f2f-960f-f3f8022a16c0"),
		'eid': 0,
		'X': 0,
		'Y': 0,
		'Z': 2,
		'Yaw': 0,
		'Pitch': 0,
		'Metadata': '\xff',
	},
	'ip2': {
		'name': "jimkilledbob",
		'uuid': UUID("30f82311-8d15-401d-b1cc-3b8b9e36cc56"),
		'eid': 1,
		'X': 2,
		'Y': 2,
		'Z': 2,
		'Yaw': 0,
		'Pitch': 0,
		'Metadata': '\xff'
	}
}

def handle(c, a):
	l, pid = readPacketHeader(c)
	if (pid == 0x00): # XXX handshake
		receiveHandshake(c)
	elif (pid == 0x0B): # XXX keep-alive
		receiveKeepAlive(c)
	else: log("Unknown pid: %s" % hex(pid))

def receiveHandshake(c): # TODO
	a = c.getpeername()
	pv, addr, port, state = readVarInt(c, name='pv'), readString(c, name='addr'), readShort(c, name='port'), readVarInt(c, name='state')
	log("New handshake from %s:%d@v%d: state %d" % (*a, pv, state))

	if (state == 1): # XXX status
		log(1, "Status")
		l, pid = readPacketHeader(c)
		if (pid == 0x00):
			fi = base64.encodebytes(open(config.favicon or '/dev/null', 'rb').read())
			sendPacket(c, 0x00, writeString(json.dumps({
				'version': {
					'name': config.version_name,
					'protocol': PV
				},
				'players': {
					'max': config.players_max,
					'online': len(players),
					'sample': [{'name': players[i]['name'], 'id': str(players[i]['uuid'])} for i in players]
				},
				'description': {
					'text': config.motd,
				},
				'favicon': "data:image/png;base64,"+fi.decode(),
			})), nolog=True)
		elif (pid == 0x01):
			log(1, "ping")
			sendPacket(c, 0x01, readLong(c))

	elif (state == 2): # XXX login
		log(1, "Login")
		if (pv != PV): sendDisconnect_login('{text="Outdated %s."}' % ('client' if (pv < PV) else 'server')); return
		l, pid = readPacketHeader(c)
		if (pid == 0x00):
			name = readString(c, 16, name='name')
			threshold = 0; sendSetCompression(c, threshold); setCompression(a, threshold)
			# TODO: encryption; compression

			uuid = uuid3(NAMESPACE_OID, ("OfflinePlayer:"+name))
			eid = max([players[i]['eid'] for i in players])
			pos = (0, 0, 0, 0, 0) # TODO
			md = '\xff' # TODO
			gamemode = config.default_gamemode
			dimension = 0
			difficulty = config.difficulty
			players_max = config.players_max
			level_type = config.level_type
			reduced_debug_info = config.reduced_debug_info
			flags = 0
			flying_speed = 1
			field_of_view_modifier = 1

			players.update({a: {
				'name': name,
				'uuid': uuid,
				'eid': eid,
				'X': pos[0],
				'Y': pos[1],
				'Z': pos[2],
				'Yaw': pos[3],
				'Pitch': pos[4],
				'Metadata': md
			}})
			sendPacket(c, 0x02, writeString(str(uuid)) + writeString(name), nolog=True)
			sendJoinGame(c,
				entity_id=eid,
				gamemode=gamemode,
				dimension=dimension,
				difficulty=difficulty,
				players_max=players_max,
				level_type=level_type,
				reduced_debug_info=reduced_debug_info
			)
			sendSpawnPosition(c, pos)
			sendPlayerAbilities(c,
				flags=flags,
				flying_speed=flying_speed,
				field_of_view_modifier=field_of_view_modifier
			)
			# C→S: Client Settings
			updatePlayerPos(c, pos)
			# C→S: Teleport Confirm
			# C→S: Player Position And Look
			# C→S: Client Status
			# S→C: Inventory, Chunk Data, Entities, etc.
			sendPacket(c, 0x20,
				writeInt(0) +
				writeInt(0) +
				writeBool(True) +
				writeVarInt(0) +
				writeVarInt(0) +
				b'' +
				writeVarInt(0) +
				b''
			)
			# TODO!
			updatePlayerList(c, 0,
				uuid=uuid,
				name=name,
				gamemode=gamemode,
				ping=0,
				has_display_name=False
			)
	else: log("Wrong state: %d" % state)

def receiveKeepAlive(c):
	sendPacket(c, 0x01, readLong(c))

def sendDisconnect_login(c, text):
	sendPacket(c, 0x00, writeString(text))

def sendSetCompression(c, threshold):
	sendPacket(c, 0x03, writeVarInt(threshold))

def sendChunk(c, pos, **args):
	chunk = None # TODO
	sendPacket(c, 0x20,
		writeInt(pos[0]) + # Chunk X
		writeInt(pos[1]) + # Chunk Y
		writeBool(data['ground_up_continuous']) + # Ground-Up Continuous
		writeVarInt(data['primary_bit_mask']) + # Primary Bit Mask
		writeVarInt(len(chunk['data'])) + # Size
		bytes().join(writeByte(i) for i in chunk['data']) + # Data
		writeVatInt(len(chunk['block_entities'])) + # Number of block entities
		bytes().join(writeString(i) for i in chunk['block_entities']) # Block entities
	)

def sendJoinGame(c, **data):
	sendPacket(c, 0x23,
		writeInt(data['entity_id']) +
		writeUByte(data['gamemode']) +
		writeInt(data['dimension']) +
		writeUByte(data['difficulty']) +
		writeUByte(data['players_max']) +
		writeString(data['level_type']) +
		writeBool(data['reduced_debug_info'])
	)

def sendPlayerAbilities(c, **data):
	sendPacket(c, 0x2C,
		writeByte(data['flags']) +
		writeFloat(data['flying_speed']) +
		writeFloat(data['field_of_view_modifier'])
	)
def sendSpawnPosition(c, pos):
	sendPacket(c, 0x46, writePosition(*pos))

def updatePlayerList(c, action, **data):
	l = 1 # TODO multiple actions
	r = (
		writeVarInt(action) +
		writeVarInt(l) +
		writeUUID(data['uuid'])
	)
	if (action == 0): # add player
		r += (
			writeString(data['name']) +
			writeVarInt(0) # TODO properties
		)
	if (action in (0, 1)): # update gamemode
		r += writeVarInt(data['gamemode'])
	if (action in (0, 2)): # update latency
		r += writeVarInt(data['ping'])
	if (action in (0, 3)): # update display name
		r += (
			writeBool(data['has_display_name']) +
			(writeString(data['display_name']) if (data['has_display_name']) else b'')
		)
	sendPacket(c, 0x2E, r)

def updatePlayerPos(c, pos, flags=0, teleport_id=0):
	sendPacket(c, 0x2F,
		writeDouble(pos[0]) +
		writeDouble(pos[1]) +
		writeDouble(pos[2]) +
		writeFloat(pos[3]) +
		writeFloat(pos[4]) +
		(writeByte(flags) if (flags != None) else b'') +
		(writeVarInt(teleport_id) if (teleport_id != None) else b'')
	)

def main():
	sethandler(handle)
	try: begin(ip=config.server_ip, port=config.server_port)
	except Exception as ex: exit(ex)
	while (True):
		try: loop()
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt: close(); exit()

if (__name__ == '__main__'): logstarted(); ll = str().join(sys.argv[1:]); setloglevel(ll.count('v')-ll.count('q')); main()
else: logimported()

# by Sdore, 2018
