#!/usr/bin/python3
# PyCraft Protocol v0 (13w41b)

from .types import *

PVs = {0}

# Handshaking
# Serverbound
Handshake = Packet(HANDSHAKING, 0x00,
	pv = VarInt, # Protocol Version
	addr = String, # Server Address
	port = UShort, # Server Port
	state = VarInt, # Next State
)

# Status
# Serverbound
StatusRequest = Packet(STATUS, 0x00)
Ping = Packet(STATUS, 0x01,
	payload = Long, # Payload
)
# Clientbound
StatusResponse = Packet(STATUS, 0x00,
	response = String, # JSON Response
)
Pong = Packet(STATUS, 0x01,
	payload = Long, # Payload
)

# Login
# Serverbound
LoginStart = Packet(LOGIN, 0x00,
	name = String, # Name
)
EncryptionRequest = Packet(LOGIN, 0x01,
	key_length = Short, # Public Key Length
	key = Data, # Public Key
	token_length = Short, # Verify Token Length
	token = Data, # Verify Token
)
# Clientbound
LoginDisconnect = Packet(LOGIN, 0x00,
	reason = String, # JSON Data
)
EncryptionResponse = Packet(LOGIN, 0x01,
	server_id = String, # Server ID
	key_length = Short, # Public Key Length
	key = Data, # Public Key
	token_length = Short, # Verify Token Length
	token = Data, # Verify Token
)
LoginSuccess = Packet(LOGIN, 0x02,
	uuid = String, # UUID
	name = String, # Username
)

# Play
# Serverbound
KeepAlive_S = Packet(PLAY, 0x00,
	id = Int, # Keep Alive ID
)
ChatMessage_S = Packet(PLAY, 0x01,
	message = String, # JSON Data
)
UseEntity = Packet(PLAY, 0x02,
	target = Int, # Target
	mouse = Byte, # Mouse
)
Player = Packet(PLAY, 0x03,
	on_ground = Bool, # On Ground
)
PlayerPosition = Packet(PLAY, 0x04,
	x = Double, # X
	y = Double, # Y
	stance = Double, # Stance
	z = Double, # Z
	on_ground = Bool, # On Ground
)
PlayerLook = Packet(PLAY, 0x05,
	yaw = Float, # Yaw
	pitch = Float, # Pitch
	on_ground = Bool, # On Ground
)
PlayerPositionAndLook_S = Packet(PLAY, 0x06,
	x = Double, # X
	y = Double, # Y
	stance = Double, # Stance
	z = Double, # Z
	yaw = Float, # Yaw
	pitch = Float, # Pitch
	on_ground = Bool, # On Ground
)
PlayerDigging = Packet(PLAY, 0x07,
	status = Byte, # Status
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	face = Byte, # Face
)
DIGGING_START = Const(0)
DIGGING_CANCEL = Const(1)
DIGGING_FINISH = Const(2)
DROP_ITEM_STACK = Const(3)
DROP_ITEM = Const(4)
ITEM_USAGE_FINISH = Const(5)
PlayerBlockPlacement = Packet(PLAY, 0x08,
	x = Int, # X
	y = UByte, # Y
	z = Int, # Z
	direction = Byte, # Direction
	held_item = 'Slot', # Held Item # TODO: Slot
	cursor_x = Byte, # Cursor position X
	cursor_y = Byte, # Cursor position Y
	cursor_z = Byte, # Cursor position Z
)
HeldItemChange_S = Packet(PLAY, 0x09,
	slot = Short, # Slot
)
Animation_S = Packet(PLAY, 0x0A,
	eid = Int, # Entity (Player) ID
	animation = Byte, # Animation ID
)
EntityAction = Packet(PLAY, 0x0B,
	eid = Int, # Entity (Player) ID
	action_id = Byte, # Action ID
	jump_boost = Int, # Jump Boost
)
CROUCH = Const(1)
UNCROUCH = Const(2)
LEAVE_BED = Const(3)
SPRINT_START = Const(4)
SPRINT_STOP = Const(5)
SteerVehicle = Packet(PLAY, 0x0C,
	sideways = Float, # Sideways
	forward = Float, # Forward
	jump = Bool, # Jump
	Unmount = Bool, # Unmount
)
CloseWindow_S = Packet(PLAY, 0x0D,
	window_id = Byte, # Window ID
)
ClickWindow = Packet(PLAY, 0x0E,
	window_id = Byte, # Window ID
	slot = Short, # Slot
	button = Byte, # Button
	action_id = Short, # Action number
	mode = Byte, # Mode
	item = 'Slot', # Clicked item # TODO: Slot
)
ConfirmTransaction_S = Packet(PLAY, 0x0F,
	window_id = Byte, # Window ID
	action_id = Short, # Action number
	accepted = Bool, # Accepted
)
CreativeInventoryAction = Packet(PLAY, 0x10,
	slot = Short, # Slot
	item = 'Slot', # Clicked item # TODO: Slot
)
EnchantItem = Packet(PLAY, 0x11,
	window_id = Byte, # Window ID
	enchantment = Byte, # Enchantment
)
UpdateSign_S = Packet(PLAY, 0x12,
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	line_1 = String, # Line 1
	line_2 = String, # Line 2
	line_3 = String, # Line 3
	line_4 = String, # Line 4
)
PlayerAbilities_S = Packet(PLAY, 0x13,
	flags = Byte, # Flags
	flying_speed = Float, # Flying Speed
	walking_speed = Float, # Walking Speed
)
TabComplete_S = Packet(PLAY, 0x14,
	text = String, # Text
)
ClientSettings = Packet(PLAY, 0x15,
	locale = String, # Locale
	view_distance = Byte, # View Distance
	chat_flags = Byte, # Chat Flags
	_ = Bool, # ???
	difficulty = Byte, # Difficulty
	show_cape = Bool, # Show Cape
)
ClientStatus = Packet(PLAY, 0x16,
	action_id = Byte, # Action ID
)
RESPAWN = Const(1)
STATS_REQUEST = Const(2)
OPEN_INVENTORY_ACHIEVEMENT = Const(3)
PluginMessage_S = Packet(PLAY, 0x17, # TODO: think on arrays parsing on versioning level
	channel = String, # Channel
	length = Short, # Length
	data = Data, # Data
)

# Clientbound
KeepAlive_C = Packet(PLAY, 0x00,
	id = Int, # Keep Alive ID
)
JoinGame = Packet(PLAY, 0x01,
	eid = Int, # Entity ID
	gamemode = UByte, # Gamemode
	dimension = Byte, # Dimension
	difficulty = UByte, # Difficulty
	players_max = UByte, # Max Players
)
ChatMessage_C = Packet(PLAY, 0x02,
	message = String, # JSON Data
)
TimeUpdate = Packet(PLAY, 0x03,
	age = Long, # Age of the world
	time = Long, # Time of day
)
EntityEquipment = Packet(PLAY, 0x04,
	eid = Int, # Entity ID
	slot = Short, # Slot
	item = 'Slot', # Item # TODO: Slot
)
SpawnPosition = Packet(PLAY, 0x05,
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
)
UpdateHealth = Packet(PLAY, 0x06,
	health = Float, # Health
	food = Short, # Food
	saturation = Float, # Food Saturation
)
Respawn = Packet(PLAY, 0x07,
	dimension = Int, # Dimension
	difficulty = UByte, # Difficulty
	gamemode = UByte, # Gamemode
)
PlayerPositionAndLook_C = Packet(PLAY, 0x08,
	x = Double, # X
	y = Double, # Y
	z = Double, # Z
	yaw = Float, # Yaw,
	pitch = Float, # Pitch
	on_ground = Bool, # On Ground
)
HeldItemChange_C = Packet(PLAY, 0x09,
	slot = Byte, # Slot
)
UseBed = Packet(PLAY, 0x0A,
	eid = Int, # Entity (Player) ID
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
)
Animation_C = Packet(PLAY, 0x0B,
	eid = VarInt, # Entity (Player) ID
	animation = UByte, # Animation ID
)
SpawnPlayer = Packet(PLAY, 0x0C,
	eid = VarInt, # Entity (Player) ID
	uuid = String, # Player UUID
	name = String, # Player Name
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	yaw = Byte, # Yaw
	pitch = Byte, # Pitch
	item = Short, # Current Item
	metadata = 'Metadata', # Metadata # TODO: Metadata
)
CollectItem = Packet(PLAY, 0x0D,
	collected_eid = Int, # Collected Entity ID
	collector_eid = Int, # Collector Entity ID
)
SpawnObject = Packet(PLAY, 0x0E,
	eid = VarInt, # Entity ID
	type = Byte, # Type
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	pitch = Byte, # Pitch
	yaw = Byte, # Yaw
	data = Int, # Object Data (https://wiki.vg/Object_Data)
)
SpawnMob = Packet(PLAY, 0x0F,
	eid = VarInt, # Entity ID
	type = Byte, # Type
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	pitch = Byte, # Pitch
	head_pitch = Byte, # Head Pitch
	yaw = Byte, # Yaw
	velocity_x = Short, # Velocity X
	velocity_y = Short, # Velocity Y
	velocity_z = Short, # Velocity Z
	metadata = 'Metadata', # Metadata # TODO: Metadata
)
SpawnPainting = Packet(PLAY, 0x10,
	eid = VarInt, # Entity ID
	title = String, # Title
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	direction = Int, # Direction
)
SpawnExperienceOrb = Packet(PLAY, 0x11,
	eid = VarInt, # Entity ID
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	count = Short, # Count (XP)
)
EntityVelocity = Packet(PLAY, 0x12,
	eid = Int, # Entity ID
	velocity_x = Short, # Velocity X
	velocity_y = Short, # Velocity Y
	velocity_z = Short, # Velocity Z
)
DestroyEntities = Packet(PLAY, 0x13, # TODO: think on arrays parsing on versioning level
	count = Byte, # Count
	eids = Data, # Entity IDs
)
Entity = Packet(PLAY, 0x14,
	eid = Int, # Entity ID
)
EntityRelativeMove = Packet(PLAY, 0x15,
	eid = Int, # Entity ID
	dx = Byte, # DX
	dy = Byte, # DY
	dz = Byte, # DZ
)
EntityLook = Packet(PLAY, 0x16,
	eid = Int, # Entity ID
	yaw = Byte, # Yaw
	pitch = Byte, # Pitch
)
EntityLookAndRelativeMove = Packet(PLAY, 0x17,
	eid = Int, # Entity ID
	dx = Byte, # DX
	dy = Byte, # DY
	dz = Byte, # DZ
	yaw = Byte, # Yaw
	pitch = Byte, # Pitch
)
EntityTeleport = Packet(PLAY, 0x18,
	eid = Int, # Entity ID
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	yaw = Byte, # Yaw
	pitch = Byte, # Pitch
)
EntityHeadLook = Packet(PLAY, 0x19,
	eid = Int, # Entity ID
	head_yaw = Byte, # Head Yaw
)
EntityStatus = Packet(PLAY, 0x1A,
	eid = Int, # Entity ID
	status = Byte, # Entity Status
)
ENTITY_HURT = Const(2)
ENTITY_DEAD = Const(3)
WOLF_TAMING = Const(6)
WOLF_TAMED = Const(7)
WOLF_SHAKING = Const(8)
EATING_ACCEPTED = Const(9)
SHEEP_EATING = Const(10)
IRON_GOLEM_ROSE = Const(11)
VILLAGER_LOVES = Const(12)
VILLAGER_ANGRY = Const(13)
VILLAGER_HAPPY = Const(14)
WITCH_MAGIC = Const(15)
ZOMBIE_VILLAGER_HEALING = Const(16)
FIREWORK_EXPLODING = Const(17)
AttachEntity = Packet(PLAY, 0x1B,
	eid = Int, # Entity ID
	vehicle_eid = Int, # Vehicle ID
	leash = Bool, # Leash
)
EntityEffect = Packet(PLAY, 0x1C,
	eid = Int, # Entity ID
	metadata = 'Metadata', # Metadata # TODO: Metadata
)
EntityEffect = Packet(PLAY, 0x1D,
	eid = Int, # Entity ID
	effect_id = Byte, # Effect ID
	amplifier = Byte, # Amplifier
	duration = Short, # Duration
)
RemoveEntityEffect = Packet(PLAY, 0x1E,
	eid = Int, # Entity ID
	effect_id = Byte, # Effect ID
)
SetExperience = Packet(PLAY, 0x1F,
	bar = Float, # Experience bar
	level = Short, # Level
	total = Short, # Total Experience
)
EntityProperties = Packet(PLAY, 0x20, # TODO: think on arrays parsing on versioning level
	eid = Int, # Entity ID
	count = Int, # Count
	properties = Data, # Properties
)
ChunkData = Packet(PLAY, 0x21, # TODO: think on arrays parsing on versioning level
	chunk_x = Int, # Chunk X
	chunk_z = Int, # Chunk Z
	guc = Bool, # Ground-Up Continuous
	pbm = UShort, # Primary bitmap
	abm = UShort, # Add bitmap
	size = Int, # Compressed size
	data = Data, # Compressed data
)
MultiBlockChange = Packet(PLAY, 0x22, # TODO: think on arrays parsing on versioning level
	chunk_x = VarInt, # Chunk X
	chunk_z = VarInt, # Chunk Z
	count = Short, # Record count
	size = Int, # Data size
	data = Data, # Records
)
BlockChange = Packet(PLAY, 0x23,
	x = Int, # X
	y = UByte, # Y
	z = Int, # Z
	type = VarInt, # Block Type
	data = UByte, # Block Data
)
BlockAction = Packet(PLAY, 0x24,
	x = Int, # X
	y = UByte, # Y
	z = Int, # Z
	byte_1 = UByte, # Byte 1 (https://wiki.vg/Block_Actions)
	byte_2 = UByte, # Byte 2 (https://wiki.vg/Block_Actions)
	type = VarInt, # Block Type
)
BlockBreakAnimation = Packet(PLAY, 0x25,
	eid = VarInt, # Entity ID
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
	stage = Byte # Destroy Stage
)
MapChunkBulk = Packet(PLAY, 0x26, # TODO: think on arrays parsing on versioning level
	count = Short, # Chunk column count
	size = Int, # Data length
	sky_light_sent = Bool, # Sky light sent
	data = Data, # Compressed chunk data
	chunk_x = Int, # Chunk X
	chunk_z = Int, # Chunk Z
	pbm = UShort, # Primary bitmap
	abm = UShort, # Add bitmap
)
Explosion = Packet(PLAY, 0x27, # TODO: think on arrays parsing on versioning level
	x = Float, # X
	y = Float, # Y
	z = Float, # Z
	radius = Float, # Radius
	count = Int, # Record count
	data = Data, # Records
	dx = Float, # Player Motion X
	dy = Float, # Player Motion Y
	dz = Float, # Player Motion Z
)
Effect = Packet(PLAY, 0x28,
	eid = Int, # Effect ID
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	data = Int, # Data
	drv = Bool, # Disable relative volume
)
SoundEffect = Packet(PLAY, 0x29,
	name = String, # Sound name
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	volume = Float, # Volume
	pitch = UByte, # Pitch
	category = UByte, # Sound Category
)
Particle = Packet(PLAY, 0x2A,
	name = String, # Particle name
	x = Float, # X
	y = Float, # Y
	z = Float, # Z
	offset_x = Float, # Offset X
	offset_y = Float, # Offset Y
	offset_z = Float, # Offset Z
	speed = Float, # Particle Speed
	number = Int, # Number of particles
)
ChangeGameState = Packet(PLAY, 0x2B,
	reason = UByte, # Reason
	value = Float, # Value
)
INVALID_BED = Const(0)
RAINING_BEGIN = Const(1)
RAINING_END = Const(2)
CHANGE_GAMEMODE = Const(3)
ENTER_CREDITS = Const(4)
DEMO_MESSAGE = Const(5)
BOW_HIT = Const(6)
FADE_VALUE = Const(7)
FADE_TIME = Const(8)
SpawnGlobalEntity = Packet(PLAY, 0x2C,
	eid = VarInt, # Entity ID
	type = Byte, # Type
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
)
OpenWindow = Packet(PLAY, 0x2D,
	window_id = UByte, # Window ID
	type = UByte, # Inventory Type
	title = String, # Window title
	slots = UByte, # Number of Slots
	custom_title = Bool, # Use provided window title (see 'title' field above)
	eid = Int, # Entity ID # TODO: optional!
)
CloseWindow_C = Packet(PLAY, 0x2E,
	window_id = UByte, # Window ID
)
SetSlot = Packet(PLAY, 0x2F,
	window_id = UByte, # Window ID
	slot = Short, # Slot
	data = 'Slot', # Slot data # TODO: Slot
)
WindowItems = Packet(PLAY, 0x30, # TODO: think on arrays parsing on versioning level
	window_id = UByte, # Window ID
	count = Short, # Count
	data = Data, # Slot Data
)
WindowProperty = Packet(PLAY, 0x31,
	window_id = UByte, # Window ID
	property = Short, # Property
	value = Short, # Value
)
ConfirmTransaction_C = Packet(PLAY, 0x32,
	window_id = UByte, # Window ID
	action_id = Short, # Action number
	accepted = Bool, # Accepted
)
UpdateSign_C = Packet(PLAY, 0x33,
	x = Int, # X
	y = Byte, # Y
	z = Int, # Z
	line_1 = String, # Line 1
	line_2 = String, # Line 2
	line_3 = String, # Line 3
	line_4 = String, # Line 4
)
Maps = Packet(PLAY, 0x34, # TODO: think on arrays parsing on versioning level
	item_damage = VarInt, # Item Damage
	length = Short, # Length
	data = Data, # Data
)
UpdateBlockEntity = Packet(PLAY, 0x35, # TODO: think on arrays parsing on versioning level
	x = Int, # X
	y = Short, # Y
	z = Int, # Z
	action_id = UByte, # Action ID
	length = Short, # Length
	nbt_data = Data, # NBT Data
)
MOB_IN_SPAWNER = Const(1)
SignEditorOpen = Packet(PLAY, 0x36,
	x = Int, # X
	y = Int, # Y
	z = Int, # Z
)
Statistics = Packet(PLAY, 0x37, # TODO: think on arrays parsing on versioning level
	count = VarInt, # Count
	data = Data, # dummy, see format below
	# [
	#	name = String, # Statistic's name
	#	amount = VarInt, # Amount
	# ]
)
PlayerListItem = Packet(PLAY, 0x38,
	name = String, # Player Name
	online = Bool, # Online
	Ping = Short, # Ping
)
PlayerAbilities_C = Packet(PLAY, 0x39,
	flags = Byte, # Flags
	flying_speed = Float, # Flying Speed
	walking_speed = Float, # Walking Speed
)
TabComplete_C = Packet(PLAY, 0x3A, # TODO: think on arrays parsing on versioning level
	count = VarInt, # Count
	matches = Data, # Match [array of String]
)
ScoreboardObjective = Packet(PLAY, 0x3B,
	name = String, # Objective name
	value = String, # Objective value
	action_id = Byte, # Create/Remove/Update
)
SCOREBOARD_CREATE = Const(0)
SCOREBOARD_REMOVE = Const(1)
SCOREBOARD_UPDATE = Const(2)
UpdateScore = Packet(PLAY, 0x3C,
	name = String, # Item Name
	action_id = Byte, # Update/Remove
	score_name = String, # Score Name # TODO: optional!
	value = Int, # Value # TODO: optional!
)
DisplayScoreboard = Packet(PLAY, 0x3D,
	position = Byte, # Position
	score_name = String, # Score Name
)
Teams = Packet(PLAY, 0x3E, # TODO: think on arrays parsing on versioning level
	name = String, # Team Name
	mode = Byte, # Mode
	display_name = String, # Team Display Name # TODO: optional!
	prefix = String, # Team Prefix # TODO: optional!
	suffix = String, # Team Suffix # TODO: optional!
	friendly_fire = Byte, # Friendly fire # TODO: optional!
	count = Short, # Player count # TODO: optional!
	players = Data, # Data [array of String] # TODO: optional!
)
TEAM_CREATE = Const(0)
TEAM_REMOVE = Const(1)
TEAM_UPDATE = Const(2)
TEAM_PLAYER_ADD = Const(3)
TEAM_PLAYER_REMOVE = Const(4)
PluginMessage_C = Packet(PLAY, 0x3F,
	channel = String, # Channel
	length = Short, # Length
	data = Data, # Data
)
Disconnect = Packet(PLAY, 0x40,
	reason = String, # Reason
)

# TODO: rename fields after their wiki.vg's names instead of commenting [maybe]
# TODO: flags consts

# фуф, как же я задолбался это писать...
# by Sdore, 2019
