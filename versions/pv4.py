#!/usr/bin/python3
# PyCraft Protocol v4 (1.7.2-1.7.5)

from .pv1_3 import *

PVs = {4}

# Play
# Clientbound
MultiBlockChange = Packet(PLAY, 0x22, # TODO: think on arrays parsing on versioning level
	chunk_x = Int, # Chunk X
	chunk_z = Int, # Chunk Z
	count = Short, # Record count
	size = Int, # Data size
	data = Data, # Records
)
SetSlot = Packet(PLAY, 0x2F,
	window_id = Byte, # Window ID
	slot = Short, # Slot
	data = 'Slot', # Slot data # TODO: Slot
)

# by Sdore, 2018
