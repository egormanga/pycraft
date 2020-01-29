#!/usr/bin/python3
# PyCraft Protocol v5 (1.7.6-1.7.10)
# https://wiki.vg/Protocol?oldid=6003

from .pv4 import *; S, C = ver()

PVs = {5}
MCV = ('1.7.6', '1.7.10')


""" Play """

# Clientbound

C.SpawnPlayer = Packet(PLAY, 0x0C,
	eid = VarInt,
	uuid = String,
	name = String,
	data_count = Length[VarInt, 'data'],
	data = Array[Struct (
		name = String,
		value = String,
		signature = String,
	), 'data_count'],
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
	yaw = Byte,
	pitch = Byte,
	item = Short,
	metadata = EntityMetadata,
)

# by Sdore, 2019
