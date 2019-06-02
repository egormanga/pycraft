#!/usr/bin/python3
# PyCraft Protocol v1-3 (13w42a-1.7.1)

from .pv0 import *

PVs = {1, 2, 3}

# Play
# Clientbound
JoinGame = Packet(PLAY, 0x01,
	eid = Int, # Entity ID
	gamemode = UByte, # Gamemode
	dimension = Byte, # Dimension
	difficulty = UByte, # Difficulty
	players_max = UByte, # Max Players
	level_type = String, # Level Type
)
Respawn = Packet(PLAY, 0x07,
	dimension = Int, # Dimension
	difficulty = UByte, # Difficulty
	gamemode = UByte, # Gamemode
	level_type = String, # Level Type
)
SoundEffect = Packet(PLAY, 0x29,
	name = String, # Sound name
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	volume = Float, # Volume
	pitch = UByte, # Pitch
)

# by Sdore, 2019
