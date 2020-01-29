#!/usr/bin/python3
# PyCraft Protocol v47 (1.8-1.8.9)
# https://wiki.vg/Protocol?oldid=7368

from .pv5 import *; S, C = ver()

PVs = {47}
MCV = ('1.8', '1.8.9')


class Position:
	_default = (0, 0, 0)

	@staticmethod
	def read(c, *, ctx=None):
		v = ULong.read(c, ctx=ctx)
		x = v >> 38 & 0x3FFFFFF
		z = v >> 12 & 0x3FFFFFF
		y = v & 0xFFF
		if (x >= 1 << 25): x -= 1 << 26
		if (y >= 1 << 11): y -= 1 << 12
		if (z >= 1 << 25): z -= 1 << 26
		return (x, y, z)

	@staticmethod
	def pack(v, *, ctx=None):
		x, y, z = map(int, v)
		return ULong.pack(
			(x & 0x3FFFFFF) << 38 |
			(z & 0x3FFFFFF) << 12 |
			 y & 0xFFF,
		ctx=ctx)

ChunkSection = Struct (
	block_count = Short,
	bits_per_block = UByte,
	palette = Optional[Struct (
		length = Length[VarInt, 'palette'],
		palette = Array[VarInt, 'length'],
	), 'bits_per_block', lambda bits_per_block: bits_per_block < 9],
	length = Length[VarInt, 'data'],
	data = Array[Long, 'length'],
)
Chunk = Struct (
	data = Array[ChunkSection, 'pbm', lambda pbm: sum(1 for i in range(16) if pbm & (1 << i))],
	biomes = Optional[Array[Int, 256], 'full_section'],
)


""" Login """


# Serverbound

S.EncryptionResponse = Packet(LOGIN, 0x01,
	server_id = String,
	key_length = Length[VarInt, 'key'],
	key = Array[Byte, 'key_length'],
	token_length = Length[VarInt, 'token'],
	token = Array[Byte, 'token_length'],
)


# Clientbound

C.EncryptionRequest = Packet(LOGIN, 0x01,
	key_length = Length[VarInt, 'key'],
	key = Array[Byte, 'key_length'],
	token_length = Length[VarInt, 'token'],
	token = Array[Byte, 'token_length'],
)

C.SetCompression = Packet(LOGIN, 0x03,
	threshold = VarInt,
)


""" Play """


# Serverbound

S.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = VarInt,
)

S.UseEntity = Packet(PLAY, 0x02,
	target = VarInt,
	type = Enum[VarInt] (
		INTERACT	= 0,
		ATTACK		= 1,
		INTERACT_AT	= 2,
	),
	target_x = Optional[Float, 'type', 2],
	target_y = Optional[Float, 'type', 2],
	target_z = Optional[Float, 'type', 2],
)

S.PlayerPosition = Packet(PLAY, 0x04,
	x = Double,
	y = Double,
	z = Double,
	on_ground = Bool,
)

S.PlayerPositionAndLook = Packet(PLAY, 0x06,
	x = Double,
	y = Double,
	z = Double,
	yaw = Float,
	pitch = Float,
	on_ground = Bool,
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
	action = Enum[UByte] (
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

S.TabComplete = Packet(PLAY, 0x14,
	text = String,
	has_position = Bool,
	looked_at_block = Optional[Position, 'has_position'],
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
	action = Enum[UByte] (
		RESPAWN = 1,
		STATS_REQUEST = 2,
		OPEN_INVENTORY_ACHIEVEMENT = 3,
	),
)

S.PluginMessage = Packet(PLAY, 0x17,
	channel = String,
	data = Data,
)

S.Spectate = Packet(PLAY, 0x18,
	target_uuid = UUID,
)

S.ResourcePackStatus = Packet(PLAY, 0x19,
	hash = String,
	result = Enum[VarInt] (
		SUCCESSFULLY_LOADED	= 0,
		DECLINED		= 1,
		DOWNLOAD_FAILED	= 2,
		ACCEPTED		= 3,
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

C.EntityEquipment = Packet(PLAY, 0x04,
	eid = VarInt,
	slot = Enum[Short] (
		HELD		= 0,
		BOOTS		= 1,
		LEGGINGS	= 2,
		CHESTPLATE	= 3,
		HELMET		= 4,
	),
	item = Slot,
)

C.SpawnPosition = Packet(PLAY, 0x05,
	pos = Position,
)

C.UpdateHealth = Packet(PLAY, 0x06,
	health = Float,
	food = VarInt,
	saturation = Float,
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
	eid = VarInt,
	pos = Position,
)

C.SpawnPlayer = Packet(PLAY, 0x0C,
	eid = VarInt,
	uuid = String,
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
	yaw = Byte,
	pitch = Byte,
	item = Short,
	metadata = EntityMetadata,
)

C.CollectItem = Packet(PLAY, 0x0D,
	collected_eid = VarInt,
	collector_eid = VarInt,
)

C.SpawnPainting = Packet(PLAY, 0x10,
	eid = VarInt,
	title = String(13),
	pos = Position,
	direction = Enum[UByte] (
		Z_NEG = 0,
		X_NEG = 1,
		Z_POS = 2,
		X_POS = 3,
	),
)

C.EntityVelocity = Packet(PLAY, 0x12,
	eid = VarInt,
	dx = Short,
	dy = Short,
	dz = Short,
)

C.DestroyEntities = Packet(PLAY, 0x13,
	count = Length[VarInt, 'eids'],
	eids = Array[VarInt, 'count'],
)

C.Entity = Packet(PLAY, 0x14,
	eid = VarInt,
)

C.EntityRelativeMove = Packet(PLAY, 0x15,
	eid = VarInt,
	dx = Fixed[Byte],
	dy = Fixed[Byte],
	dz = Fixed[Byte],
	on_ground = Bool,
)

C.EntityLook = Packet(PLAY, 0x16,
	eid = VarInt,
	yaw = Byte,
	pitch = Byte,
	on_ground = Bool,
)

C.EntityLookAndRelativeMove = Packet(PLAY, 0x17,
	eid = VarInt,
	dx = Fixed[Byte],
	dy = Fixed[Byte],
	dz = Fixed[Byte],
	yaw = Byte,
	pitch = Byte,
	on_ground = Bool,
)

C.EntityTeleport = Packet(PLAY, 0x18,
	eid = VarInt,
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
	yaw = Byte,
	pitch = Byte,
	on_ground = Bool,
)

C.EntityHeadLook = Packet(PLAY, 0x19,
	eid = VarInt,
	head_yaw = Byte,
)

C.EntityMetadata = Packet(PLAY, 0x1C,
	eid = VarInt,
	metadata = EntityMetadata,
)

C.EntityEffect = Packet(PLAY, 0x1D,
	eid = VarInt,
	effect_id = Byte,
	amplifier = Byte,
	duration = VarInt,
	hide_particles = Bool,
)

C.RemoveEntityEffect = Packet(PLAY, 0x1E,
	eid = VarInt,
	effect_id = Byte,
)

C.SetExperience = Packet(PLAY, 0x1F,
	bar = Float,
	level = VarInt,
	total = VarInt,
)

C.EntityProperties = Packet(PLAY, 0x20,
	eid = VarInt,
	count = Length[VarInt, 'properties'],
	properties = Array[Struct (
		key = Enum[String] (
			MAX_HEALTH				= 'generic.maxHealth',
			FOLLOW_RANGE				= 'generic.followRange',
			KNOCKBACK_RESISTANCE			= 'generic.knockbackResistance',
			MOVEMENT_SPEED				= 'generic.movementSpeed',
			ATTACK_DAMAGE				= 'generic.attackDamage',
			HORSE_JUMP_STRENGTH			= 'horse.jumpStrength',
			ZOMBIE_SPAWN_REINFORCEMENTS_CHANCE	= 'zombie.spawnReinforcements',
		),
		value = Double,
		length = Length[Short, 'modifiers'],
		modifiers = Array[Struct (
			uuid = UUID,
			amount = Double,
			operation = Enum[Byte] (
				ADD_SUM	= 0,
				MUL_SUM	= 1,
				MUL_PROD	= 2,
			),
		), 'length'],
	), 'count'],
)

C.ChunkData = Packet(PLAY, 0x21,
        chunk_x = Int,
        chunk_z = Int,
        full_section = Bool,
        pbm = UShort,
        size = Size[VarInt, 'data'],
        data = Chunk,
)

C.MultiBlockChange = Packet(PLAY, 0x22,
	chunk_x = VarInt,
	chunk_z = VarInt,
	count = Length[Short, 'records'],
	records = Array[Struct (
		hpos = Mask[UByte] (
			X = 0xF0,
			Z = 0x0F,
		),
		y = UByte,
		id = VarInt,
	), 'count'],
)

C.BlockChange = Packet(PLAY, 0x23,
	pos = Position,
	id = VarInt,
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

C.MapChunkBulk = Packet(PLAY, 0x26,
	sky_light_sent = Bool,
	count = Length[Short, 'meta'],
	meta = Array[Struct (
		chunk_x = Int,
		chunk_z = Int,
		pbm = UShort,
		abm = UShort,
	), 'count'],
	data = Array[Chunk, 'count'],
)

C.Effect = Packet(PLAY, 0x28,
	eid = Int,
	pos = Position,
	data = Int,
	drv = Bool,
)

C.Particle = Packet(PLAY, 0x2A,
	id = int, # TODO: enum
	long_distance = Bool,
	x = Float,
	y = Float,
	z = Float,
	offset_x = Float,
	offset_y = Float,
	offset_z = Float,
	particle_data = Float,
	number = Int,
	data = Array[VarInt, 0], # TODO: "iconcrack"(36) has length of 2, "blockcrack"(37), and "blockdust"(38) have lengths of 1, the rest have 0.
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

C.MapData = Packet(PLAY, 0x34,
	item_damage = VarInt,
	scale = Byte,
	icon_count = Length[VarInt, 'icons'],
	icons = Array[Struct (
		direction_and_type = Mask[Byte] (
			TYPE		= 0x0F,
			DIRECTION	= 0xF0,
		),
		x = Byte,
		y = Byte,
	), 'icon_count'],
	columns = Byte,
	rows = Optional[Byte, 'columns'],
	x = Optional[Byte, 'columns'],
	y = Optional[Byte, 'columns'],
	length = Optional[Length[VarInt, 'data'], 'columns'],
	data = Optional[Array[UByte, 'length'], 'columns'],
)

C.UpdateBlockEntity = Packet(PLAY, 0x35,
	pos = Position,
	action = Enum[UByte] (
		MOB_IN_SPAWNER = 1,
	),
	length = Length[Short, 'nbt_data'],
	nbt_data = Optional[NBT, 'length'],
)

C.SignEditorOpen = Packet(PLAY, 0x36,
	pos = Position,
)

C.PlayerListItem = Packet(PLAY, 0x38,
	action = Enum[VarInt] (
	),
	#count = Length[VarInt, 'players'],
	#players = Array[Struct (
	#	uuid = UUID,
	#	name = Optional[String, 'action', 0],
	#	number_of_properties = Optional[VarInt, 'action', 0],
	#	
	#), 'count'],
	data = Data, # TODO
)

C.ScoreboardObjective = Packet(PLAY, 0x3B,
	name = String,
	action = Enum[Byte] (
		CREATE = 0,
		REMOVE = 1,
		UPDATE = 2,
	),
	value = Optional[String, 'action', (0, 2)],
	type = Optional[String, 'action', (0, 2)],
)

C.UpdateScore = Packet(PLAY, 0x3C,
	name = String,
	action = Enum[Byte] (
		UPDATE = 0,
		REMOVE = 1,
	),
	score_name = String,
	value = VarInt,
)

C.Teams = Packet(PLAY, 0x3E,
	name = String,
	mode = Enum[Byte] (
		CREATE		= 0,
		REMOVE		= 1,
		UPDATE		= 2,
		PLAYER_ADD	= 3,
		PLAYER_REMOVE	= 4,
	),
	display_name = Optional[String, 'mode', (0, 2)],
	prefix = Optional[String, 'mode', (0, 2)],
	suffix = Optional[String, 'mode', (0, 2)],
	friendly_fire = Optional[Enum[Byte] (
		OFF			= 0,
		ON			= 1,
		FRIENDLY_INVISIBLE	= 3,
	), 'mode', (0, 2)],
	name_tag_visibility = Optional[Enum[String] (
		ALWAYS			= 'always',
		HIDE_FOR_OTHER_TEAMS	= 'hideForOtherTeams',
		HIDE_FOR_OWN_TEAM	= 'hideForOwnTeam',
		NEVER			= 'never',
	), 'mode', (0, 2)],
	color = Optional[Byte, 'mode', (0, 2)],
	count = Optional[Length[VarInt, 'players'], 'mode', (0, 3, 4)],
	players = Optional[Array[String, 'count'], 'mode', (0, 3, 4)],
)

C.PluginMessage = Packet(PLAY, 0x3F,
	channel = String,
	data = Data,
)

C.ServerDifficulty = Packet(PLAY, 0x41,
	difficulty = Enum[UByte] (
		PEACEFUL = 0,
		EASY = 1,
		NORMAL = 2,
		HARD = 3,
	),
)

C.CombatEvent = Packet(PLAY, 0x42,
	event = Enum[VarInt] (
		ENTER_COMBAT	= 0,
		END_COMBAT	= 1,
		ENTITY_DEAD	= 2,
	),
	duration = Optional[VarInt, 'event', 1],
	player_id = Optional[VarInt, 'event', 2],
	eid = Optional[Int, 'event', (1, 2)],
	message = Optional[String, 'event', 2],
)

C.Camera = Packet(PLAY, 0x43,
	camera_eid = VarInt,
)

C.WorldBorder = Packet(PLAY, 0x44,
	action = Enum[VarInt] (
	),
	data = Data, # TODO
)

C.Title = Packet(PLAY, 0x45,
	action = Enum[VarInt] (
		SET_TITLE		= 0,
		SET_SUBTITLE		= 1,
		SET_TIMES_AND_DISPLAY	= 2,
		HIDE			= 3,
		RESET			= 4,
	),
	title = Optional[Chat, 'action', 0],
	subtitle = Optional[Chat, 'action', 1],
	fade_in = Optional[Int, 'action', 2],
	stay = Optional[Int, 'action', 2],
	fade_out = Optional[Int, 'action', 2],
)

C.SetCompression = Packet(PLAY, 0x46, # Warning: This packet is completely broken and has been removed in the 1.9 snapshots. The packet C.SetCompression(LOGIN, 0x03) should be used instead.
	threshold = VarInt,
)

C.PlayerListHeaderAndFooter = Packet(PLAY, 0x47,
	header = Chat,
	footer = Chat,
)

C.ResourcePackSend = Packet(PLAY, 0x48,
	url = String,
	hash = String,
)

C.UpdateEntityNBT = Packet(PLAY, 0x49,
	eid = VarInt,
	tag = NBT,
)

# by Sdore, 2020
