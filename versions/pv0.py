#!/usr/bin/python3
# PyCraft Protocol v0 (13w41b)

__all__ = {
	'Handshake',

	'StatusRequest',
	'StatusResponse',
	'Ping',
	'Pong',

	'LoginStart',
	'LoginDisconnect',
	'LoginSuccess',

	'KeepAlive',
	'JoinGame',
	'SpawnPosition',
	'Player_S',
	'PlayerPosition_S',
	'PlayerLook_S',
	'PlayerPositionAndLook_S',
	'PlayerPositionAndLook_C',
	'PlayerAbilities',
}

from ..protocol import *

PV = 0

# Handshaking
class Handshake:
	state, pid = HANDSHAKING, 0x00
	def send(c, pv, addr, port, state): return c.sendPacket(Handshake,
		writeVarInt(pv), # Protocol Version
		writeString(addr), # Server Address
		writeUShort(port), # Server Port
		writeVarInt(state), # Next State
	)
	def recv(c): return (
		readVarInt(c), # Protocol Version
		readString(c), # Server Address
		readUShort(c), # Server Port
		readVarInt(c), # Next State
	)

# Status
class StatusRequest:
	state, pid = STATUS, 0x00
	def send(c): return c.sendPacket(StatusRequest)
	def recv(c): return ()
class StatusResponse:
	state, pid = STATUS, 0x00
	def send(c, response): return c.sendPacket(StatusResponse,
		writeString(response), # JSON Response
	)
	def recv(c): return (
		readString(c), # Json Response
	)
class Ping:
	state, pid = STATUS, 0x01
	def send(c, payload): return c.sendPacket(Ping,
		writeLong(payload), # Payload
	)
	def recv(c): return (
		readLong(c), # Payload
	)
Pong = Ping # same packet

# Login
class LoginStart:
	state, pid = LOGIN, 0x00
	def send(c, name): return c.sendPacket(LoginStart,
		writeString(name), # Name
	)
	def recv(c): return (
		readString(c), # Name
	)
class LoginDisconnect:
	state, pid = LOGIN, 0x00
	def send(c, reason): return c.sendPacket(LoginDisconnect,
		writeString(reason), # JSON Data
	)
	def recv(c): return (
		readString(c), # JSON Data
	)
class LoginSuccess:
	state, pid = LOGIN, 0x02
	def send(c, uuid, name): return c.sendPacket(LoginSuccess,
		writeString(uuid), # UUID
		writeString(name), # Username
	)
	def recv(c): return (
		readString(c), # UUID
		readString(c), # Username
	)

# Play
class KeepAlive:
	state, pid = PLAY, 0x00
	def send(c, id): return c.sendPacket(KeepAlive,
		writeInt(id), # Keep Alive ID
	)
	def recv(c): return (
		readInt(c), # Keep Alive ID
	)
class JoinGame:
	state, pid = PLAY, 0x01
	def send(c, eid, gamemode, dimension, difficulty, players_max): return c.sendPacket(JoinGame,
		writeInt(eid), # Entity ID
		writeUByte(gamemode), # Gamemode
		writeByte(dimension), # Dimension
		writeUByte(difficulty), # Difficulty
		writeUByte(players_max), # Max Players
	)
#..
class SpawnPosition:
	state, pid = PLAY, 0x05
	def send(c, pos): return c.sendPacket(SpawnPosition,
		writeInt(pos.x), # X
		writeInt(pos.y), # Y
		writeInt(pos.z), # Z
	)
class Player_S:
	state, pid = PLAY, 0x03
	def recv(c): return (
		readBool(c), # On Ground
	)
class PlayerPosition_S:
	state, pid = PLAY, 0x04
	def recv(c): return (
		readDouble(c), # X
		readDouble(c), # Y
		readDouble(c), # Stance
		readDouble(c), # X
		readBool(c), # On Ground
	)
class PlayerLook_S:
	state, pid = PLAY, 0x05
	def recv(c): return (
		readFloat(c), # Yaw
		readFloat(c), # Pitch
		readBool(c), # On Ground
	)
class PlayerPositionAndLook_S:
	state, pid = PLAY, 0x06
	def recv(c): return (
		readDouble(c), # X
		readDouble(c), # Y
		readDouble(c), # Stance
		readDouble(c), # X
		readFloat(c), # Yaw
		readFloat(c), # Pitch
		readBool(c), # On Ground
	)
#..
class PlayerPositionAndLook_C:
	state, pid = PLAY, 0x08
	def send(c, pos): return c.sendPacket(PlayerPositionAndLook_C,
		writeDouble(pos.x), # X
		writeDouble(pos.y), # Y
		writeDouble(pos.z), # Z
		writeFloat(pos.yaw), # Yaw
		writeFloat(pos.pitch), # Pitch
		writeBool(pos.on_ground), # On Ground
	)
#..
class PlayerAbilities:
	state, pid = PLAY, 0x39
	def send(c, flags, flying_speed, walking_speed): return c.sendPacket(PlayerAbilities,
		writeByte(flags), # Flags
		writeFloat(flying_speed), # Flying Speed
		writeFloat(walking_speed), # Walking Speed
	)
#..
class PluginMessage: # TODO think on length [PRIVATE]
	state, pid = PLAY, 0x3F
	def send(c, ns, v, data): return c.sendPacket(PluginMessage,
		writeIdentifier(ns, v), # Channel
		data, # Data
	)

# by Sdore, 2018
