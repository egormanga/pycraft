#!/usr/bin/python3
# PyCraft Protocol base / v0 (13w41b)

from ..commons import State, DISCONNECTED, HANDSHAKING, STATUS, LOGIN, PLAY
import copy, json, uuid, ctypes, string, struct, inspect
from nbt import *
from utils import hex, dispatch, staticitemget, Sdict, Slist

PVs = {0}
MCV = ('13w41b',)*2


class _Generic:
	@classmethod
	def read(cls, c, *, ctx=None):
		t = '>'+cls.f
		return struct.unpack(t, c.read(struct.calcsize(t)))[0]

	@classmethod
	def readn(cls, c, n, *, ctx=None):
		t = '>'+str(n)+cls.f
		return struct.unpack(t, c.read(struct.calcsize(t)))

	@classmethod
	def pack(cls, v, *, ctx=None):
		return struct.pack('>'+cls.f, cls.t(float(v) if (cls.f in 'fd') else int(v)).value)

	@classmethod
	def packn(cls, n, *v, ctx=None):
		return struct.pack('>'+str(n)+cls.f, *(cls.t(float(i) if (cls.f in 'fd') else int(i)).value for i in v))
class Bool(_Generic): f, t = '?', ctypes.c_bool
class Byte(_Generic): f, t = 'b', ctypes.c_byte
class UByte(_Generic): f, t = 'B', ctypes.c_ubyte
class Short(_Generic): f, t = 'h', ctypes.c_short
class UShort(_Generic): f, t = 'H', ctypes.c_ushort
class Int(_Generic): f, t = 'i', ctypes.c_int
class UInt(_Generic): f, t = 'I', ctypes.c_uint
class Long(_Generic): f, t = 'q', ctypes.c_longlong
class ULong(_Generic): f, t = 'Q', ctypes.c_ulonglong
class Float(_Generic): f, t = 'f', ctypes.c_float
class Double(_Generic): f, t = 'd', ctypes.c_double

class String:
	__slots__ = ('length',)

	def __init__(self, length):
		self.length = length

	@staticmethod
	@dispatch
	def read(c, ctx, *, length=32767):
		s = c.read(VarInt.read(c, ctx=ctx)).decode('utf8')
		assert (len(s) <= length)
		return s

	@dispatch
	def read(self, c, *, ctx=None):
		return self.read(c, ctx, self.length)

	@staticmethod
	@dispatch
	def pack(v, ctx, *, length=32767):
		assert (len(v) <= length)
		s = v.encode('utf-8')
		return VarInt.pack(len(s), ctx=ctx) + s

	@dispatch
	def pack(self, v, *, ctx=None):
		return self.pack(v, ctx, length=self.length)

class JSON:
	@staticmethod
	def read(c, *, ctx=None):
		return json.loads(String.read(c, ctx=ctx))

	@staticmethod
	def pack(v, *, ctx=None):
		return String.pack(json.dumps(v, separators=',:', ensure_ascii=False), ctx=ctx)
class Chat(JSON): pass

class Identifier(String):
	ns_chars = string.digits+string.ascii_lowercase+'_-'
	name_chars = ns_chars+'/.'

	@classmethod
	def pack(cls, v, *, ctx=None):
		ns, name = v.split(':')
		assert all(c in ns_chars for c in ns)
		assert all(c in name_chars for c in name)
		return String.pack(ns+':'+name, ctx=ctx)

class _VarIntBase:
	@classmethod
	def read(cls, c, *, ctx=None):
		r = int()
		i = int()
		for i in range(cls.length):
			b = (c.read(1) or b'\0')[0]
			r |= (b & (1 << 7)-1) << (7*i)
			if (not b & (1 << 7)): break
		else: raise \
			ValueError(f"{cls.__name__} is too big")
		return r

	@classmethod
	def pack(cls, v, *, ctx=None):
		r = bytearray()
		while (True):
			c = v & (1 << 7)-1
			v >>= 7
			if (v): c |= (1 << 7)
			r.append(c)
			if (not v): break
		assert (len(r) <= cls.length)
		return bytes(r)

class VarInt(_VarIntBase):
	length = 5

	@classmethod
	def read(cls, c, *, ctx=None):
		return ctypes.c_int(super().read(c, ctx=ctx)).value

	@classmethod
	def pack(cls, v, *, ctx=None):
		return super().pack(ctypes.c_uint(v).value, ctx=ctx)

class VarLong(_VarIntBase):
	length = 10

	@classmethod
	def read(cls, c, *, ctx=None):
		return ctypes.c_long(super().read(c, ctx=ctx)).value

	@classmethod
	def pack(cls, v, *, ctx=None):
		return super().pack(ctypes.c_ulong(v).value, ctx=ctx)

class EntityMetadata: # TODO: https://wiki.vg/Entity_metadata#Entity_Metadata_Format
	@staticmethod
	def read(cls, c, *, ctx=None):
		r = dict()
		while (True):
			b = UByte.read(c, ctx=ctx)
			if (b == 127): break
			k, t = b & 0x1F, b >> 5
			r[k] = (Byte, Short, Int, Float, String, Slot, Struct (
				x = Int,
				y = Int,
				z = Int
			))[t].read(c, ctx=ctx)
		return r

	### TODO:
	#@classmethod
	#def pack(cls, v, *, ctx=None):
	#	r = bytearray()
	#	for k, v in v.items():
	#		r += Byte.pack((cls.types.index(type(v)) << 5 | k & 0x1F) & 0xFF) + 
	###

class NBT:
	@staticmethod
	def read(c, *, ctx=None):
		return nbt.NBTFile(buffer=c.makefile())

	@staticmethod
	def pack(v, *, ctx=None):
		r = io.BytesIO()
		v.write_file(buffer=r)
		return r.getvalue()

class Position:
	@staticmethod
	def read(c, *, ctx=None):
		v = ULong.read(c, ctx=ctx)
		x = v >> 38
		y = v & 0xFFF
		z = v << 26 >> 38
		if (x >= 1 << 25): x -= 1 << 26
		if (y >= 1 << 11): y -= 1 << 12
		if (z >= 1 << 25): z -= 1 << 26
		return (x, y, z)

	@staticmethod
	def pack(v, *, ctx=None):
		x, y, z = map(int, v)
		return ULong.pack(
			((x & 0x3FFFFFF) << 38) |
			((y & 0xFFF) << 26) |
			 (z & 0x3FFFFFF),
		ctx)

class Angle(Byte): pass

class UUID:
	@staticmethod
	def read(c, *, ctx=None):
		return uuid.UUID(bytes=c.read(16))

	@staticmethod
	def pack(v, *, ctx=None):
		return v.bytes

@staticitemget
class Fixed:
	def __init__(self, type, fracbits):
		self.type, self.fracbits = type, fracbits

	def read(self, c, *, ctx=None):
		return self.type.read(c, ctx=ctx) / (1 << self.fracbits)

	def pack(self, v, *, ctx=None):
		return self.type.pack(int(v*(1 << self.fracbits)), ctx=ctx)

@staticitemget
class Optional:
	def __init__(self, type, flag_name, flag_values=None):
		self.type, self.flag_name = type, flag_name

	def read(self, c, *, ctx=None):
		f = ctx[self.flag_name]
		if (f in self.flag_values if (self.flag_values is not None) else f): return self.type.read(c, ctx=ctx)

	def pack(self, v, *, ctx=None):
		f = ctx[self.flag_name]
		if (f in self.flag_values if (self.flag_values is not None) else f): return self.type.pack(v, ctx=ctx)
		return b''

@staticitemget
class Array:
	_default = []

	def __init__(self, type, count):
		self.type, self.count = type, count

	def read(self, c, *, ctx=None):
		return self.type.readn(c, ctx[self.count] if (isinstance(self.count, str)) else self.count, ctx=ctx)

	def pack(self, v, *, ctx=None):
		return self.type.packn(ctx[self.count] if (isinstance(self.count, str)) else self.count, *v, ctx=ctx)

@staticitemget
class Enum:
	def __init__(self, type):
		self._type = type

	def __call__(self, *, _default=None, **fields):
		self.__dict__.update(fields)
		self._default = _default
		return self

	def read(self, c, *, ctx=None):
		return self._type.read(c, ctx=ctx)

	def pack(self, v, *, ctx=None):
		try: v = getattr(self, v)
		except (TypeError, AttributeError): pass
		return self._type.pack(v, ctx=ctx)
@staticitemget
class Flags(Enum.f): pass

class Struct:
	def __init__(self, **fields):
		self.fields = fields

	def __getattr__(self, x):
		try: return self.__getattribute__('fields')[x]
		except KeyError: pass
		raise AttributeError(x)

	def read(self, c, *, ctx=None):
		r = Sdict()
		if (ctx is None): ctx = r
		for k, v in self.fields.items():
			r[k] = v.read(c, ctx=ctx)
		return copy.deepcopy(r) if (ctx is r) else r

	def pack(self, v, *, ctx=None):
		if (ctx is None): ctx = Sdict()
		r = bytearray()
		for k in Slist((*v, *self.fields)).uniquize():
			if (k not in self.fields): continue
			ctx[k] = v[k] if (k in v) else self.fields[k]._default
			r += self.fields[k].pack(ctx[k], ctx=ctx)
		return bytes(r)

class Packet:
	__slots__ = ('state', 'pid', 'struct')

	def __init__(self, _state, _pid, **fields):
		self.state, self.pid, self.struct = _state, _pid, Struct(**fields)

	def __repr__(self):
		return f"<Packet state={self.state} pid={hex(self.pid)}>"

	def __getattr__(self, x):
		return getattr(self.__getattribute__('struct'), x)

	def send(self, c, *, nolog=True, **fields):
		return c.sendPacket(self, self.struct.pack(fields), nolog=nolog)

	def recv(self, c):
		return Sdict(self.struct.read(c))

Slot = Struct (
	present = Bool,
	item_id = Optional[VarInt, 'present'],
	item_count = Optional[Byte, 'present'],
	nbt = Optional[NBT, 'present'],
)

class _Version: pass
S = _Version()
C = _Version()
def ver():
	globals = inspect.stack()[1][0].f_globals
	return (copy.deepcopy(globals['S']), copy.deepcopy(globals['C']))


""" Handshaking """


# Serverbound

S.Handshake = Packet(HANDSHAKING, 0x00,
	pv = VarInt,
	addr = String,
	port = UShort,
	state = VarInt,
)


""" Status """


# Serverbound

S.StatusRequest = Packet(STATUS, 0x00)

S.Ping = Packet(STATUS, 0x01,
	payload = Long,
)


# Clientbound

C.StatusResponse = Packet(STATUS, 0x00,
	response = JSON,
)

C.Pong = Packet(STATUS, 0x01,
	payload = Long,
)


""" Login """


# Serverbound

S.LoginStart = Packet(LOGIN, 0x00,
	name = String,
)

S.EncryptionRequest = Packet(LOGIN, 0x01,
	key_length = Short,
	key = Array[Byte, 'key_length'],
	token_length = Short,
	token = Array[Byte, 'token_length'],
)


# Clientbound

C.LoginDisconnect = Packet(LOGIN, 0x00,
	reason = JSON,
)

C.EncryptionResponse = Packet(LOGIN, 0x01,
	server_id = String,
	key_length = Short,
	key = Array[Byte, 'key_length'],
	token_length = Short,
	token = Array[Byte, 'token_length'],
)

C.LoginSuccess = Packet(LOGIN, 0x02,
	uuid = String,
	username = String,
)


""" Play """


# Serverbound

S.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = Int,
)

S.ChatMessage = Packet(PLAY, 0x01,
	message = String,
)

S.UseEntity = Packet(PLAY, 0x02,
	target = Int,
	mouse = Byte,
)

S.Player = Packet(PLAY, 0x03,
	on_ground = Bool,
)

S.PlayerPosition = Packet(PLAY, 0x04,
	x = Double,
	y = Double,
	head_y = Double,
	z = Double,
	on_ground = Bool,
)

S.PlayerLook = Packet(PLAY, 0x05,
	yaw = Float,
	pitch = Float,
	on_ground = Bool,
)

S.PlayerPositionAndLook = Packet(PLAY, 0x06,
	x = Double,
	y = Double,
	head_y = Double,
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
	x = Int,
	y = Byte,
	z = Int,
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
	x = Int,
	y = UByte,
	z = Int,
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

S.HeldItemChange = Packet(PLAY, 0x09,
	slot = Short,
)

S.Animation = Packet(PLAY, 0x0A,
	eid = Int,
	animation = Enum[Byte] (
		NONE = 0,
		SWING_ARM = 1,
		DAMAGE = 2,
		LEAVE_BED = 3,
		EAT_FOOD = 5,
		CRITICAL_EFFECT = 6,
		MAGIC_CRITICAL_EFFECT = 7,
		CROUCH = 104,
		UNCROUCH = 105,
	),
)

S.EntityAction = Packet(PLAY, 0x0B,
	eid = Int,
	action_id = Enum[Byte] (
		CROUCH = 1,
		UNCROUCH = 2,
		LEAVE_BED = 3,
		SPRINT_START = 4,
		SPRINT_STOP = 5,
	),
	horse_jump_boost = Int,
)

S.SteerVehicle = Packet(PLAY, 0x0C,
	sideways = Float,
	forward = Float,
	jump = Bool,
	unmount = Bool,
)

S.CloseWindow = Packet(PLAY, 0x0D,
	window_id = Byte,
)

S.ClickWindow = Packet(PLAY, 0x0E,
	window_id = Byte,
	slot = Short,
	button = Byte,
	action_id = Short,
	mode = Byte,
	item = Slot,
)

S.ConfirmTransaction = Packet(PLAY, 0x0F,
	window_id = Byte,
	action_id = Short,
	accepted = Bool,
)

S.CreativeInventoryAction = Packet(PLAY, 0x10,
	slot = Short,
	item = Slot,
)

S.EnchantItem = Packet(PLAY, 0x11,
	window_id = Byte,
	enchantment = Byte,
)

S.UpdateSign = Packet(PLAY, 0x12,
	x = Int,
	y = Byte,
	z = Int,
	lines = Array[String, 4],
)

S.PlayerAbilities = Packet(PLAY, 0x13,
	flags = Flags[Byte] (
		CREATIVE_MODE = 0x01,
		FLYING = 0x02,
		ALLOW_FLYING = 0x04,
		INVULNERABLE = 0x08,
	),
	flying_speed = Float,
	walking_speed = Float,
)

S.TabComplete = Packet(PLAY, 0x14,
	text = String,
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
	difficulty = Byte,
	show_cape = Bool,
)

S.ClientStatus = Packet(PLAY, 0x16,
	action_id = Enum[Byte] (
		RESPAWN = 1,
		STATS_REQUEST = 2,
		OPEN_INVENTORY_ACHIEVEMENT = 3,
	),
)

S.PluginMessage = Packet(PLAY, 0x17,
	channel = String,
	length = Short,
	data = Array[Byte, 'length'],
)


# Clientbound

C.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = Int,
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
)

C.ChatMessage = Packet(PLAY, 0x02,
	message = JSON,
)

C.TimeUpdate = Packet(PLAY, 0x03,
	age = Long,
	time = Long,
)

C.EntityEquipment = Packet(PLAY, 0x04,
	eid = Int,
	slot = Enum[Short] (
		HELD = 0,
		BOOTS = 1,
		LEGGINGS = 2,
		CHESTPLATE = 3,
		HELMET = 4,
	),
	item = Slot,
)

C.SpawnPosition = Packet(PLAY, 0x05,
	x = Int,
	y = Int,
	z = Int,
)

C.UpdateHealth = Packet(PLAY, 0x06,
	health = Float,
	food = Short,
	saturation = Float,
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
)

C.PlayerPositionAndLook = Packet(PLAY, 0x08,
	x = Double,
	y = Double,
	z = Double,
	yaw = Float,
	pitch = Float,
	on_ground = Bool,
)

C.HeldItemChange = Packet(PLAY, 0x09,
	slot = Byte,
)

C.UseBed = Packet(PLAY, 0x0A,
	eid = Int,
	x = Int,
	y = Byte,
	z = Int,
)

C.Animation = Packet(PLAY, 0x0B,
	eid = VarInt,
	animation = Enum[UByte] (
		NONE = 0,
		SWING_ARM = 1,
		DAMAGE = 2,
		LEAVE_BED = 3,
		EAT_FOOD = 5,
		CRITICAL_EFFECT = 6,
		MAGIC_CRITICAL_EFFECT = 7,
		CROUCH = 104,
		UNCROUCH = 105,
	),
)

C.SpawnPlayer = Packet(PLAY, 0x0C,
	eid = VarInt,
	uuid = String,
	name = String,
	x = Int,
	y = Int,
	z = Int,
	yaw = Byte,
	pitch = Byte,
	item = Short,
	metadata = EntityMetadata,
)

C.CollectItem = Packet(PLAY, 0x0D,
	collected_eid = Int,
	collector_eid = Int,
)

C.SpawnObject = Packet(PLAY, 0x0E, # TODO: https://wiki.vg/Entity_metadata#Objects
	eid = VarInt,
	type = Byte,
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
	pitch = Byte,
	yaw = Byte,
	data = Int, # https://wiki.vg/Object_Data
)

C.SpawnMob = Packet(PLAY, 0x0F, # TODO: https://wiki.vg/Entity_metadata#Objects
	eid = VarInt,
	type = Byte,
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
	pitch = Byte,
	head_pitch = Byte,
	yaw = Byte,
	dx = Short,
	dy = Short,
	dz = Short,
	metadata = EntityMetadata,
)

C.SpawnPainting = Packet(PLAY, 0x10,
	eid = VarInt,
	title = String(13),
	x = Int,
	y = Int,
	z = Int,
	direction = Enum[Int] (
		Z_NEG = 0,
		X_NEG = 1,
		Z_POS = 2,
		X_POS = 3,
	),
)

C.SpawnExperienceOrb = Packet(PLAY, 0x11,
	eid = VarInt,
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
	count = Short,
)

C.EntityVelocity = Packet(PLAY, 0x12,
	eid = Int,
	dx = Short,
	dy = Short,
	dz = Short,
)

C.DestroyEntities = Packet(PLAY, 0x13,
	count = Byte,
	eids = Array[Int, 'count'],
)

C.Entity = Packet(PLAY, 0x14,
	eid = Int,
)

C.EntityRelativeMove = Packet(PLAY, 0x15,
	eid = Int,
	dx = Byte,
	dy = Byte,
	dz = Byte,
)

C.EntityLook = Packet(PLAY, 0x16,
	eid = Int,
	yaw = Byte,
	pitch = Byte,
)

C.EntityLookAndRelativeMove = Packet(PLAY, 0x17,
	eid = Int,
	dx = Byte,
	dy = Byte,
	dz = Byte,
	yaw = Byte,
	pitch = Byte,
)

C.EntityTeleport = Packet(PLAY, 0x18,
	eid = Int,
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
	yaw = Byte,
	pitch = Byte,
)

C.EntityHeadLook = Packet(PLAY, 0x19,
	eid = Int,
	head_yaw = Byte,
)

C.EntityStatus = Packet(PLAY, 0x1A,
	eid = Int,
	status = Enum[Byte] (
		ENTITY_HURT = 2,
		ENTITY_DEAD = 3,
		WOLF_TAMING = 6,
		WOLF_TAMED = 7,
		WOLF_SHAKING = 8,
		EATING_ACCEPTED = 9,
		SHEEP_EATING = 10,
		IRON_GOLEM_ROSE = 11,
		VILLAGER_LOVES = 12,
		VILLAGER_ANGRY = 13,
		VILLAGER_HAPPY = 14,
		WITCH_MAGIC = 15,
		ZOMBIE_VILLAGER_HEALING = 16,
		FIREWORK_EXPLODING = 17,
	),
)

C.AttachEntity = Packet(PLAY, 0x1B,
	eid = Int,
	vehicle_eid = Int,
	leash = Bool,
)

C.EntityMetadata = Packet(PLAY, 0x1C,
	eid = Int,
	metadata = EntityMetadata,
)

C.EntityEffect = Packet(PLAY, 0x1D,
	eid = Int,
	effect_id = Byte,
	amplifier = Byte,
	duration = Short,
)

C.RemoveEntityEffect = Packet(PLAY, 0x1E,
	eid = Int,
	effect_id = Byte,
)

C.SetExperience = Packet(PLAY, 0x1F,
	bar = Float,
	level = Short,
	total = Short,
)

C.EntityProperties = Packet(PLAY, 0x20,
	eid = Int,
	count = Int,
	properties = Array[Struct (
		key = Enum[String] (
			MAX_HEALTH = 'generic.maxHealth',
			FOLLOW_RANGE = 'generic.followRange',
			KNOCKBACK_RESISTANCE = 'generic.knockbackResistance',
			MOVEMENT_SPEED = 'generic.movementSpeed',
			ATTACK_DAMAGE = 'generic.attackDamage',
			HORSE_JUMP_STRENGTH = 'horse.jumpStrength',
			ZOMBIE_SPAWN_REINFORCEMENTS_CHANCE = 'zombie.spawnReinforcements',
		),
		value = Double,
		length = Short,
		modifiers = Array[Struct (
			uuid = UUID,
			amount = Double,
			operation = Enum[Byte] (
				ADD_SUM = 0,
				MUL_SUM = 1,
				MUL_PROD = 2,
			),
		), 'length'],
	), 'count'], # Properties
)

C.ChunkData = Packet(PLAY, 0x21,
	chunk_x = Int,
	chunk_z = Int,
	guc = Bool,
	pbm = UShort,
	abm = UShort,
	size = Int,
	data = Array[Byte, 'size'],
)

C.MultiBlockChange = Packet(PLAY, 0x22,
	chunk_x = VarInt,
	chunk_z = VarInt,
	count = Short,
	size = Int,
	data = Array[UInt, 'count'],
)

C.BlockChange = Packet(PLAY, 0x23,
	x = Int,
	y = UByte,
	z = Int,
	id = VarInt,
	data = UByte,
)

C.BlockAction = Packet(PLAY, 0x24,
	x = Int,
	y = UByte,
	z = Int,
	data = Array[UByte, 2], # https://wiki.vg/Block_Actions
	id = VarInt,
)

C.BlockBreakAnimation = Packet(PLAY, 0x25,
	eid = VarInt,
	x = Int,
	y = Int,
	z = Int,
	stage = Byte,
)

C.MapChunkBulk = Packet(PLAY, 0x26,
	count = Short,
	size = Int,
	sky_light_sent = Bool,
	data = Array[Byte, 'size'],
	chunk_x = Int,
	chunk_z = Int,
	pbm = UShort,
	abm = UShort,
)

C.Explosion = Packet(PLAY, 0x27,
	x = Float,
	y = Float,
	z = Float,
	radius = Float,
	count = Int,
	records = Array[Struct (
		x = Byte,
		y = Byte,
		z = Byte,
	), 'count'],
	dx = Float,
	dy = Float,
	dz = Float,
)

C.Effect = Packet(PLAY, 0x28,
	eid = Int,
	x = Int,
	y = Byte,
	z = Int,
	data = Int,
	drv = Bool,
)

C.SoundEffect = Packet(PLAY, 0x29,
	name = String,
	x = Int,
	y = Byte,
	z = Int,
	volume = Float,
	pitch = UByte,
	category = Enum[UByte] (
		MASTER = 0,
		MUSIC = 1,
		RECORDS = 2,
		WEATHER = 3,
		BLOCKS = 4,
		MOBS = 5,
		ANIMALS = 6,
		PLAYERS = 7,
	),
)

C.Particle = Packet(PLAY, 0x2A,
	name = String,
	x = Float,
	y = Float,
	z = Float,
	offset_x = Float,
	offset_y = Float,
	offset_z = Float,
	speed = Float,
	number = Int,
)

C.ChangeGameState = Packet(PLAY, 0x2B,
	reason = Enum[UByte] (
		INVALID_BED = 0,
		RAINING_BEGIN = 1,
		RAINING_END = 2,
		CHANGE_GAMEMODE = 3,
		ENTER_CREDITS = 4,
		DEMO_MESSAGE = 5,
		BOW_HIT = 6,
		FADE_VALUE = 7,
		FADE_TIME = 8,
	),
	value = Float,
)

C.SpawnGlobalEntity = Packet(PLAY, 0x2C,
	eid = VarInt,
	type = Enum[Byte] (
		THUNDERBOLT = 1,
	),
	x = Fixed[Int, 5],
	y = Fixed[Int, 5],
	z = Fixed[Int, 5],
)

C.OpenWindow = Packet(PLAY, 0x2D,
	window_id = UByte,
	type = UByte, # TODO: https://wiki.vg/Inventory#Windows
	title = String,
	slots = UByte,
	custom_title = Bool,
	eid = Int,
)

C.CloseWindow = Packet(PLAY, 0x2E,
	window_id = UByte,
)

C.SetSlot = Packet(PLAY, 0x2F,
	window_id = UByte,
	slot = Short,
	slot_data = Slot,
)

C.WindowItems = Packet(PLAY, 0x30,
	window_id = UByte,
	count = Short,
	slot_data = Array[Slot, 'count'],
)

C.WindowProperty = Packet(PLAY, 0x31,
	window_id = UByte,
	property = Enum[Short] (
		FURNACE_PROGRESS = 0,
		FURNACE_FUEL = 1,
	),
	value = Short,
)

C.ConfirmTransaction = Packet(PLAY, 0x32,
	window_id = UByte,
	action_id = Short,
	accepted = Bool,
)

C.UpdateSign = Packet(PLAY, 0x33,
	x = Int,
	y = Byte,
	z = Int,
	lines = Array[String, 4],
)

C.Maps = Packet(PLAY, 0x34, # TODO parse array
	item_damage = VarInt,
	length = Short,
	data = Array[Byte, 'length'],
)

C.UpdateBlockEntity = Packet(PLAY, 0x35,
	x = Int,
	y = Short,
	z = Int,
	action_id = Enum[UByte] (
		MOB_IN_SPAWNER = 1,
	),
	length = Short,
	nbt_data = Optional[NBT, 'length'],
)

C.SignEditorOpen = Packet(PLAY, 0x36,
	x = Int,
	y = Int,
	z = Int,
)

C.Statistics = Packet(PLAY, 0x37,
	count = VarInt,
	data = Array[Struct (
		name = String,
		amount = VarInt,
	), 'count'],
)

C.PlayerListItem = Packet(PLAY, 0x38,
	name = String,
	online = Bool,
	Ping = Short,
)

C.PlayerAbilities = Packet(PLAY, 0x39,
	flags = Flags[Byte] (
		INVULNERABLE = 0x01,
		FLYING = 0x02,
		ALLOW_FLYING = 0x04,
		CREATIVE_MODE = 0x08,
	),
	flying_speed = Float,
	walking_speed = Float,
)

C.TabComplete = Packet(PLAY, 0x3A,
	count = VarInt,
	matches = Array[String, 'count'],
)

C.ScoreboardObjective = Packet(PLAY, 0x3B,
	name = String,
	value = String,
	action_id = Enum[Byte] (
		CREATE = 0,
		REMOVE = 1,
		UPDATE = 2,
	),
)

C.UpdateScore = Packet(PLAY, 0x3C,
	name = String,
	action_id = Enum[Byte] (
		UPDATE = 0,
		REMOVE = 1,
	),
	score_name = String,
	value = Int,
)

C.DisplayScoreboard = Packet(PLAY, 0x3D,
	position = Enum[Byte] (
		LIST = 0,
		SIDEBAR = 1,
		BELOW_NAME = 2,
	),
	score_name = String,
)

C.Teams = Packet(PLAY, 0x3E,
	name = String,
	mode = Enum[Byte] (
		CREATE = 0,
		REMOVE = 1,
		UPDATE = 2,
		PLAYER_ADD = 3,
		PLAYER_REMOVE = 4,
	),
	display_name = Optional[String, 'mode', (0, 2)],
	prefix = Optional[String, 'mode', (0, 2)],
	suffix = Optional[String, 'mode', (0, 2)],
	friendly_fire = Optional[Enum[Byte] (
		OFF = 0,
		ON = 1,
		FRIENLY_INVISIBLE = 3,
	), 'mode', (0, 2)],
	count = Optional[Short, 'mode', (0, 3, 4)],
	players = Optional[Array[String, 'count'], 'mode', (0, 3, 4)],
)

C.PluginMessage = Packet(PLAY, 0x3F,
	channel = String,
	length = Short,
	data = Array[Byte, 'length'],
)

C.Disconnect = Packet(PLAY, 0x40,
	reason = Chat,
)

# TODO: replace all assertions with exceptions

# by Sdore, 2019
