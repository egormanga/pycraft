#!/usr/bin/python3
# PyCraft Protocol v4 (1.7.2-1.7.5)
# https://wiki.vg/Protocol?oldid=5486

from .pv1_3 import *; S, C = ver()

PVs = {4}
MCV = ('1.7.2', '1.7.5')


""" Play """


# Clientbound

C.MultiBlockChange = Packet(PLAY, 0x22,
	chunk_x = Int,
	chunk_z = Int,
	count = Short,
	size = Int,
	data = Array[Mask[UInt] (
		BLOCK_DATA	= 0x0000000F,
		BLOCK_ID	= 0x0000FFF0,
		BLOCK_Y	= 0x00FF0000,
		BLOCK_Z	= 0x0F000000,
		BLOCK_X	= 0xF0000000,
	), 'count'],
)

C.SetSlot = Packet(PLAY, 0x2F,
	window_id = Byte,
	slot = Short,
	slot_data = Slot,
)

# by Sdore, 2019
