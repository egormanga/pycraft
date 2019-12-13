#!/usr/bin/python3
# PyCraft Protocol v1-3 (13w42a-1.7.1)

from .pv0 import *; S, C = ver()

PVs = {1, 2, 3}
MCV = ('13w42a', '1.7.1')


""" Play"""


# Serverbound

S.ClientStatus = Packet(PLAY, 0x16,
	action_id = Enum[Byte] (
		RESPAWN			= 0,
		STATS_REQUEST			= 1,
		OPEN_INVENTORY_ACHIEVEMENT	= 2,
	),
)


# Clientbound

C.JoinGame = Packet(PLAY, 0x01,
	eid = Int,
	gamemode = Flags[UByte] (
		SURVIVAL = 0,
		CREATIVE = 1,
		ADVENTURE = 2,
		HARDCORE = 0x8,
	),
	dimension = Enum[Byte] (
		NETHER = -1,
		OVERWORLD = 0,
		END = 1,
	),
	difficulty = Enum[UByte] (
		PEACEFUL = 0,
		EASY = 1,
		NORMAL = 2,
		HARD = 3,
	),
	players_max = UByte,
	level_type = Enum[String] (
		DEFAULT = 'default',
		FLAT = 'flat',
		LARGE_BIOMES = 'largeBiomes',
		AMPLIFIED = 'amplified',
		DEFAULT_1_1 = 'default_1_1',
	),
)

C.Respawn = Packet(PLAY, 0x07,
	dimension = Enum[Int] (
		NETHER = -1,
		OVERWORLD = 0,
		END = 1,
	),
	difficulty = Enum[UByte] (
		PEACEFUL = 0,
		EASY = 1,
		NORMAL = 2,
		HARD = 3,
	),
	gamemode = Enum[UByte] (
		SURVIVAL = 0,
		CREATIVE = 1,
		ADVENTURE = 2,
	),
	level_type = Enum[String] (
		DEFAULT = 'default',
		FLAT = 'flat',
		LARGE_BIOMES = 'largeBiomes',
		AMPLIFIED = 'amplified',
		DEFAULT_1_1 = 'default_1_1',
	),
)

C.SoundEffect = Packet(PLAY, 0x29,
	name = String,
	x = Int,
	y = Int,
	z = Int,
	volume = Float,
	pitch = UByte,
)

# by Sdore, 2019
