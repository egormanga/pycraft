#!/usr/bin/python3
# PyCraft Protocol v4 (1.7.2-1.7.5)

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
	data = Array[UInt, 'count'],
)

C.SetSlot = Packet(PLAY, 0x2F,
	window_id = Byte,
	slot = Short,
	slot_data = Slot,
)

# by Sdore, 2019
