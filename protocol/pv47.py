#!/usr/bin/python3
# PyCraft Protocol v47 (1.8-1.8.9)
# https://wiki.vg/Protocol?oldid=7368

from .pv5 import *; S, C = ver()

PVs = ()#{47} # TODO FIXME
MCV = ('1.8', '1.8.9')

# TODO:
"""
1.8
1.8-pre3
1.8-pre2
1.8-pre1

New metadata type, 7 (Rotation), 12 bytes (3 floats, Pitch, Yaw, and Roll), used on armor stand


14w34a/b/c/d
14w33a/b/c

Added new fields to Tab-Complete (Serverbound)


14w32a/b/c/d

Added new Update Entity NBT packet
Added three new fields to Use Entity


14w31a

The length prefix on the payload of Plugin Message has been removed (Both ways)
Added new Resource Pack Send packet
Added new Resource Pack Status packet
Added VarLong data type
Changed a few fields in World Border to VarLong


14w30c
14w30a/b
14w29a

Fix the length prefix of Plugin Message so that its a Varint instead of an unsigned short
Added "Long Distance" boolean to Particle


14w28b

Uncompressed NBT
Added Display name fields to Player List Item
New 'Player List Header/Footer' packet


14w28a

Changed Chunk packets to remove compression
Added packets to toggle compression/set threshold
Allowed compression for the whole protocol
Changed the Maps packet


14w27a/b
14w26c

Changed Multi Block Change to using packed block ids
Changed Block Change to using packed block ids


14w26a

Changed chunk sending


14w25b

Added boolean field to all entity movement packets


14w21a

All byte arrays have VarInt length prefixes instead of short
Spawn Player changes
Player list item changes


14w20a

Added new packet 'Title'


14w19a

Changed the Particle's 'Particle Name' to an int
Added a new field to Particle
Rewrote Player List Item
Added SET_WARNING_TIME and SET_WARNING_BLOCKS to World Border
Added new serverbound packet Spectate


14w18a

Added 'INITIALIZE' action to World Border


14w17a

Increased the max payload size of 'Plugin Message' from 32767 to 1048576 (Broken because of incorrect data type)
Added new packet 'World Border'


14w08a

Added new field 'Type' to Scoreboard Objective


14w07a

Added two new fields to Teams


14w06a

Clientbound

Added new field 'Hide Particles' to Entity Effect

Serverbound

Removed 'HeadY' from Player Position
Removed 'HeadY' from Player Position And Look


14w05a

Clientbound

New packet 'Camera'


14w04b

Spawn Painting now uses the 'Position' data type
Changed Spawn Painting's Direction type to Unsigned Byte


14w04a

Encoding for 'Position' changed

Clientbound

Changed Entity Equipment's EntityId type to VarInt
Changed Update Health's Food type to VarInt
Changed Use Bed's EntityId type to VarInt
Added new fields to Spawn Player
Changed Collect Item's EntityId(s) types to VarInt
Changed Entity Velocity's EntityId type to VarInt
Changed Destroy Entities' Length type to VarInt
Changed Destroy Entities' EntityIds type to VarInt array
Changed Entity's EntityId type to VarInt
Changed Entity Relative Move's EntityId type to VarInt
Changed Entity Look's EntityId type to VarInt
Changed Entity Look and Relative Move's EntityId type to VarInt
Changed Entity Teleport's EntityId type to VarInt
Changed Entity Head Look's EntityId type to VarInt
Changed Entity Metadata's EntityId type to Varint
Changed Entity Effect's EntityId type to VarInt
Changed Entity Effect's Duration type to VarInt
Changed Remove Entity Effect's EntityId type to VarInt
Changed Set Experience's Level type to VarInt
Changed Set Experience's Total Experience type to VarInt
Changed Entity Properties's EntityId type to VarInt
Changed Entity Properties's List Length type to VarInt
Changed Player List Item's Ping type to VarInt
Changed Update Score's Value type to VarInt
Changed Teams' Player count type to VarInt
New packet 'Combat Event'
"""


""" Play """


# Serverbound

S.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = VarInt,
)

S.UseEntity = Packet(PLAY, 0x02,
	target = VarInt,
	mouse = UByte,
)

S.PlayerDigging = Packet(PLAY, 0x07,
	status = Enum[Byte] (
		DIGGING_START = 0,
		DIGGING_CANCEL = 1,
		DIGGING_FINISH = 2,
		DROP_ITEM_STACK = 3,
		DROP_ITEM = 4,
		ITEM_USAGE_FINISH = 5,
	),
	pos = Position,
	face = Enum[Byte] (
		Y_NEG = 0,
		Y_POS = 1,
		Z_NEG = 2,
		Z_POS = 3,
		X_NEG = 4,
		X_POS = 5,
	),
)

S.PlayerBlockPlacement = Packet(PLAY, 0x08,
	pos = Position,
	face = Enum[Byte] (
		Y_NEG = 0,
		Y_POS = 1,
		Z_NEG = 2,
		Z_POS = 3,
		X_NEG = 4,
		X_POS = 5,
	),
	held_item = Slot,
	cursor_x = Byte,
	cursor_y = Byte,
	cursor_z = Byte,
)

S.Animation = Packet(PLAY, 0x0A,
	eid = Int,
	animation = Enum[Byte] (
		SWING_ARM = 0,
		DAMAGE = 1,
		LEAVE_BED = 2,
		EAT_FOOD = 3,
		CRITICAL_EFFECT = 4,
		MAGIC_CRITICAL_EFFECT = 5,
	),
)

S.EntityAction = Packet(PLAY, 0x0B,
	eid = VarInt,
	action_id = Enum[UByte] (
		CROUCH = 0,
		UNCROUCH = 1,
		LEAVE_BED = 2,
		SPRINT_START = 3,
		SPRINT_STOP = 4,
		JUMP_WITH_HORSE = 5,
		OPEN_HORSE_INVENTORY = 6,
	),
	horse_jump_boost = VarInt,
)

S.SteerVehicle = Packet(PLAY, 0x0C,
	sideways = Float,
	forward = Float,
	flags = Flags[UByte] (
		JUMP=0x1,
		UNMOUNT=0x2,
	),
)

S.UpdateSign = Packet(PLAY, 0x12,
	pos = Position,
	lines = Array[Chat, 4],
)

S.ClientSettings = Packet(PLAY, 0x15,
	locale = String,
	view_distance = Enum[Byte] (
		FAR = 0,
		NORMAL = 1,
		SHORT = 2,
		TINY = 3,
	),
	chat_flags = Flags[Byte] (
		MODE_ENABLED = 0b00,
		MODE_COMMANDS_ONLY = 0b01,
		MODE_HIDDEN = 0b10,
		COLORS = 0b1000,
	),
	chat_colors = Bool,
	skin_parts = Flags[UByte] (
		CAPE = 0x01,
		JACKET = 0x02,
		LEFT_SLEEVE = 0x04,
		RIGHT_SLEEVE = 0x08,
		LEFT_PANTS_LEG = 0x10,
		RIGHT_PANTS_LEG = 0x20,
		HAT = 0x40,
	),
)

S.ClientStatus = Packet(PLAY, 0x16,
	action_id = Enum[UByte] (
		RESPAWN = 1,
		STATS_REQUEST = 2,
		OPEN_INVENTORY_ACHIEVEMENT = 3,
	),
)


# Clientbound

C.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = VarInt,
)

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
	reduced_debug_info = Bool,
)

C.ChatMessage = Packet(PLAY, 0x02,
	message = JSON,
	position = Flags[Byte] (
		POSITION_CHAT = 0,
		POSITION_SYSTEM = 1,
		POSITION_ACTION_BAR = 2,
	_default=0),
)

C.SpawnPosition = Packet(PLAY, 0x05,
	pos = Position,
)

C.PlayerPositionAndLook = Packet(PLAY, 0x08,
	x = Double,
	y = Double,
	z = Double,
	yaw = Float,
	pitch = Float,
	flags = Flags[Byte] (
		REL_X = 0x01,
		REL_Y = 0x02,
		REL_Z = 0x04,
		REL_Y_ROT = 0x08,
		REL_X_ROT = 0x10,
	),
)

C.UseBed = Packet(PLAY, 0x0A,
	eid = Int,
	pos = Position,
)

C.BlockChange = Packet(PLAY, 0x23,
	pos = Position,
	id = VarInt,
	data = UByte,
)

C.BlockAction = Packet(PLAY, 0x24,
	pos = Position,
	data = Array[UByte, 2], # https://wiki.vg/Block_Actions
	id = VarInt,
)

C.BlockBreakAnimation = Packet(PLAY, 0x25,
	eid = VarInt,
	pos = Position,
	stage = Byte,
)

C.Effect = Packet(PLAY, 0x28,
	eid = Int,
	pos = Position,
	data = Int,
	drv = Bool,
)

C.OpenWindow = Packet(PLAY, 0x2D,
	window_id = UByte,
	type = String,
	title = String,
	slots = UByte,
	custom_title = Bool,
	eid = Int,
)

C.UpdateSign = Packet(PLAY, 0x33,
	pos = Position,
	lines = Array[String, 4],
)

C.UpdateBlockEntity = Packet(PLAY, 0x35,
	pos = Position,
	action_id = Enum[UByte] (
		MOB_IN_SPAWNER = 1,
	),
	length = Short,
	nbt_data = Optional[NBT, 'length'],
)

C.SignEditorOpen = Packet(PLAY, 0x36,
	pos = Position,
)

C.ServerDifficulty = Packet(PLAY, 0x41,
	difficulty = Enum[UByte] (
		PEACEFUL = 0,
		EASY = 1,
		NORMAL = 2,
		HARD = 3,
	),
)

# by Sdore, 2019
