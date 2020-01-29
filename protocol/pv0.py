#!/usr/bin/python3
# PyCraft Protocol base / v0 (13w41b)
# https://wiki.vg/Protocol?oldid=5007

from .. import commons
from ..commons import *

PVs = {0}
MCV = ('13w41b',)*2


class _Generic:
	_default = 0

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
	_default = ''

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
		return self.read(c, ctx, length=self.length)

	@staticmethod
	@dispatch
	def pack(v, ctx, *, length=32767):
		v = str(v)
		assert (len(v) <= length)
		s = v.encode('utf-8')
		return VarInt.pack(len(s), ctx=ctx) + s

	@dispatch
	def pack(self, v, *, ctx=None):
		return self.pack(v, ctx, length=self.length)

class JSON:
	_default = {}

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
	_default = ''

	@classmethod
	def pack(cls, v, *, ctx=None):
		ns, name = v.split(':')
		assert all(c in ns_chars for c in ns)
		assert all(c in name_chars for c in name)
		return String.pack(ns+':'+name, ctx=ctx)

class _VarIntBase:
	_default = 0

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

class NBT:
	_default = None

	@staticmethod
	def read(c, *, ctx=None):
		if ((c.getbuffer()[c.tell():c.tell()+1].tobytes() if (type(c) == io.BytesIO) else c.peek()) in b'\0\xff'): return nbt.NBTFile()
		return nbt.NBTFile(buffer=c) # TODO FIXME

	@staticmethod
	def pack(v, *, ctx=None):
		if (v is None): return b'\xff\xff'
		r = io.BytesIO()
		t = nbt.NBTFile()
		t.update(v)
		t.write_file(buffer=r)
		return r.getvalue()

class Angle(Byte): pass

class UUID:
	_default = uuid.UUID(int=0)

	@staticmethod
	def read(c, *, ctx=None):
		return uuid.UUID(bytes=c.read(16))

	@staticmethod
	def pack(v, *, ctx=None):
		return v.bytes

@staticitemget
class Fixed:
	_default = 0

	def __init__(self, type, fracbits=5):
		self.type, self.fracbits = type, fracbits

	def read(self, c, *, ctx=None):
		return self.type.read(c, ctx=ctx) / (1 << self.fracbits)

	def pack(self, v, *, ctx=None):
		return self.type.pack(int(v*(1 << self.fracbits)), ctx=ctx)

@staticitemget
class Optional:
	_default = None

	def __init__(self, type, flag_name, flag_values=None):
		self.type, self.flag_name, self.flag_values = type, flag_name, flag_values

	def __getattr__(self, x):
		return getattr(self.__getattribute__('type'), x)

	def read(self, c, *, ctx=None):
		f = ctx[self.flag_name]
		if (self.flag_values(f) if (callable(self.flag_values)) else f in self.flag_values if (isiterablenostr(self.flag_values)) else f == self.flag_values if (self.flag_values is not None) else f): return self.type.read(c, ctx=ctx)

	def pack(self, v, *, ctx=None):
		f = ctx[self.flag_name]
		if (self.flag_values(f) if (callable(self.flag_values)) else f in self.flag_values if (isiterablenostr(self.flag_values)) else f == self.flag_values if (self.flag_values is not None) else f): return self.type.pack(v, ctx=ctx)
		return b''

@staticitemget
class Array:
	_default = ()

	def __init__(self, type, count, count_func=None):
		self.type, self.count, self.count_func = type, count, count_func

	def __getattr__(self, x):
		return getattr(self.__getattribute__('type'), x)

	def read(self, c, *, ctx=None):
		n = ctx[self.count] if (isinstance(self.count, str)) else self.count
		if (self.count_func is not None): n = self.count_func(n)
		r = self.type.readn(c, n, ctx=ctx) if (hasattr(self.type, 'readn')) else [self.type.read(c, ctx=ctx) for _ in range(n)]
		return bytes(r) if (self.type == UByte) else bytes(i % 256 for i in r) if (self.type == Byte) else r

	def pack(self, v, *, ctx=None):
		try: n = ctx[self.count] if (isinstance(self.count, str)) else self.count
		except KeyError: n = len(v)
		else:
			assert (len(v) == n)
			if (self.count_func is not None): n = self.count_func(n)
		return self.type.packn(n, *v, ctx=ctx) if (hasattr(self.type, 'packn')) else bytes().join(self.type.pack(i, ctx=ctx) for i in v)

class Data:
	_default = b''

	@staticmethod
	def read(c, *, ctx=None):
		return c.read()

	@staticmethod
	def pack(self, v, *, ctx=None):
		return bytes(v)

@staticitemget
class Enum:
	def __init__(self, type):
		self.type = type

	def __call__(self, **fields):
		self.__dict__.update(fields)
		return self

	@property
	def _default(self):
		return self.type._default

	def read(self, c, *, ctx=None):
		return self.type.read(c, ctx=ctx)

	def pack(self, v, *, ctx=None):
		try: v = getattr(self, v)
		except (TypeError, AttributeError): pass
		return self.type.pack(v, ctx=ctx)
@staticitemget
class Flags(Enum.f): pass
@staticitemget
class Mask(Enum.f): pass # TODO 0xFF00(2) = 0x0200

class PackLast: pass

@staticitemget
class Length(PackLast):
	def __init__(self, type, field):
		self.type, self.field = type, field

	@property
	def _default(self):
		return self.type._default

	def read(self, c, *, ctx=None):
		r = self.type.read(c, ctx=ctx)
		assert (r == len(ctx[self.field]))
		return r

	def pack(self, v, *, ctx=None):
		return self.type.pack(v or len(ctx[self.field]), ctx=ctx)

@staticitemget
class Size(PackLast):
	def __init__(self, type, field):
		self.type, self.field = type, field

	@property
	def _default(self):
		return self.type._default

	def read(self, c, *, ctx=None):
		return self.type.read(c, ctx=ctx)

	def pack(self, v, *, ctx=None):
		return self.type.pack(v or len(ctx[self.field+'_packed']), ctx=ctx)

@staticitemget
class Zlibbed(Array.f):
	def read(self, c, *, ctx=None):
		return zlib.decompress(super().read(c, ctx=ctx))

	def pack(self, v, *, ctx=None):
		return zlib.compress(super().pack(v, ctx=ctx))

@staticitemget
class GZipped:
	class _GzipReader(gzip._GzipReader):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self._finished = None

		def _read_eof(self):
			self._finished = self._fp.file.tell()

		def _read_gzip_header(self):
			if (self._finished): return False
			return super()._read_gzip_header()

		def peek(self, l=1):
			r = self.read(l)
			self._fp.prepend(r)
			return r

	def __init__(self, type):
		self.type = type

	def read(self, c, *, ctx=None):
		r = self._GzipReader(c)
		try: return self.type.read(r, ctx=ctx)
		finally:
			if (r._finished is not None): c.seek(r._finished)

	def pack(self, v, *, ctx=None):
		return gzip.compress(self.type.pack(v, ctx=ctx))

@cachedclass
class Struct:
	_default = {}

	def __init__(self, **fields):
		self.fields = fields

	def __getattr__(self, x):
		try: return self.__getattribute__('fields')[x]
		except KeyError: pass
		raise AttributeError(x)

	def read(self, c, *, ctx=None):
		r = Sdict()
		if (ctx is None): ctx = Sdict()
		else: ctx = ctx.copy()
		for k, v in self.fields.items():
			r[k] = ctx[k] = v.read(c, ctx=ctx)
		return r

	def pack(self, v, *, ctx=None):
		if (ctx is None): ctx = Sdict()
		else: ctx = ctx.copy()
		for k, t in self.fields.items():
			if (isinstance(t, PackLast)): continue
			c = ctx[k] = v.get(k, t._default)
			ctx[k+'_packed'] = t.pack(c, ctx=ctx)
		r = bytearray()
		for k, t in self.fields.items():
			try: c = ctx[k]
			except KeyError: c = ctx[k] = v.get(k, t._default)
			try: p = ctx[k+'_packed']
			except KeyError: p = ctx[k+'_packed'] = t.pack(c, ctx=ctx)
			r += p
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

@singleton (
	item_id = Short,
	item_count = Optional[Byte, 'item_id', lambda item_id: item_id != -1],
	item_damage = Optional[Short, 'item_id', lambda item_id: item_id != -1],
	nbt = Optional[NBT, 'item_id', lambda item_id: item_id != -1],
)
class Slot(Struct.f):
	def read(self, c, *, ctx=None):
		r = super().read(c, ctx=ctx)
		if (r.nbt is None): r.nbt = nbt.NBTFile()
		if (r.item_damage is not None): r.nbt['Damage'] = nbt.TAG_Int(r.item_damage)
		return commons.Slot(id=r.item_id, count=r.item_count, nbt=r.nbt)

	def pack(self, v, *, ctx=None):
		return super().pack(dict(item_id=v.id, item_count=v.count, item_damage=v.nbt.pop('Damage', nbt.TAG_Int(0)).value, nbt=v.nbt or None), ctx=ctx)

position = Struct (
	x = Int,
	y = Int,
	z = Int,
)
look = Struct (
	pitch = Float,
	yaw = Float,
	roll = Float,
)
class EntityMetadata:
	types = (Byte, Short, Int, Float, String, Slot, position, look)
	_default = {}

	@classmethod
	def read(cls, c, *, ctx=None):
		r = Sdict()
		while (True):
			b = UByte.read(c, ctx=ctx)
			if (b == 127): break
			k, t = b & 0x1F, b >> 5
			r[k] = cls.types[t].read(c, ctx=ctx)
		s = set(r)
		for t in cls.entity_types:
			if (set(t._names) >= s): break
		else: raise WTFException(s)
		return t(**{t._names[k]: v for k, v in r.items()})

	@classmethod
	def pack(cls, v, *, ctx=None):
		if (not isinstance(v, cls._EntityMetadataBase)):
			s = set(v)
			for t in cls.entity_types:
				if (set(t._names.values()) >= s): e = t(**v); break
			else: raise WTFException(v)
		else: e = v
		r = bytearray()
		for k, v in e._names.items():
			t = e[v]
			while (t not in cls.types):
				if (t == UByte): t = Byte
				else: t = t.type
			r += UByte.pack((cls.types.index(t) << 5 | k & 0x1F) & 0xFF, ctx=ctx) + t.pack(e._data.get(v, t._default), ctx=ctx)
		r += UByte.pack(127)
		return bytes(r)

	class _MetadataMeta(type):
		def __new__(metacls, name, bases, classdict):
			newclassdict = dict()
			names = dict()
			for i in bases:
				newclassdict.update(i.__dict__)
				names.update(i._names)
			newclassdict['_names'] = names
			for k, v in classdict.items():
				m = re.match(r'_(\d+)_(\w+)', k)
				if (m is None): newclassdict[k] = v; continue
				newclassdict[m[2]] = v
				newclassdict['_names'][int(m[1])] = m[2]
			cls = super().__new__(metacls, name, bases, newclassdict)
			cls.__getitem__ = cls.__dict__.__getitem__
			#cls.__metaclass__ = metacls  # inheritance?
			return cls

	class _EntityMetadataBase(metaclass=_MetadataMeta):
		def __init__(self, **kwargs):
			self._data = {i: kwargs[i] % 256 if (self[i] == UByte) else kwargs[i] for i in self._names.values() if i in kwargs}

		@classmethod
		def __repr__(cls):
			return f"<EntityMetadata of {cls.__name__}>"

		def __str__(self):
			return str(self._data)

		def __getattribute__(self, x):
			if (x[0] == '_'): return super().__getattribute__(x)
			return self._data[x]

	class Entity(_EntityMetadataBase):
		_0_flags = Flags[Byte] (
			ON_FIRE	= 0x01,
			CROUCHED	= 0x02,
			SPRINTING	= 0x08,
			ITEM_USAGE	= 0x10,
			INVISIBLE	= 0x20,
		)
		_1_air = Short

	class LivingEntity(Entity):
		_2_name_tag = String
		_3_always_show_name_tag = Byte
		_6_health = Float
		_7_potion_effect_color = Int
		_8_potion_effect_ambient = Byte
		_9_number_of_arrows_in_entity = Byte
		_10_has_no_ai = Byte

	class Ageable(LivingEntity):
		_12_age = Int

	class ArmorStand(LivingEntity):
		_10_armorstand_flags = Flags[Byte] (
			SMALL_ARMORSTAND	= 0x01,
			HAS_GRAVITY		= 0x02,
			HAS_ARMS		= 0x04,
			HAS_BASEPLATE		= 0x08,
		)
		_11_head_position = look
		_12_body_position = look
		_13_left_arm_position = look
		_14_right_arm_position = look
		_15_left_leg_position = look
		_16_right_leg_position = look

	class Human(LivingEntity):
		_10_skin_flags = UByte
		_16_human_flags = Flags[Byte] (
			HIDE_CAPE = 0x02,
		)
		_17_absorption_hearts = Float
		_18_score = Int

	class Horse(Ageable):
		_16_horse_flags = Flags[Int] (
			IS_TAME	= 0x02,
			HAS_SADDLE	= 0x04,
			HAS_CHEST	= 0x08,
			IS_BRED	= 0x10,
			IS_EATING	= 0x20,
			IS_REARING	= 0x40,
			MOUTH_OPEN	= 0x80,
		)
		_19_horse_type = Enum[Byte] (
			HORSE		= 0,
			DONKEY		= 1,
			MULE		= 2,
			ZOMBIE		= 3,
			SKELETON	= 4,
		)
		_20_horse_color = Flags[Int] (
			COLOR_WHITE		= 0x0000,
			COLOR_CREAMY		= 0x0001,
			COLOR_CHESTNUT		= 0x0002,
			COLOR_BROWN		= 0x0003,
			COLOR_BLACK		= 0x0004,
			COLOR_GRAY		= 0x0005,
			COLOR_DARK_DOWN	= 0x0006,
			STYLE_NONE		= 0x0000,
			STYLE_WHITE		= 0x0100,
			STYLE_WHITEFIELD	= 0x0200,
			STYLE_WHITE_DOTS	= 0x0300,
			STYLE_BLACK_DOTS	= 0x0400,
		)
		_21_horse_owner_name = String
		_22_horse_armor = Enum[Int] (
			NO_ARMOR	= 0,
			IRON_ARMOR	= 1,
			GOLD_ARMOR	= 2,
			DIAMOND_ARMOR	= 3,
		)

	class Bat(LivingEntity):
		_16_bat_is_hanging = Byte

	class Tameable(Ageable):
		_16_tameable_flags = Flags[Byte] (
			IS_SITTING	= 0x01,
			IS_TAME	= 0x04,
		)
		_17_tameable_owner_name = String

	class Ocelot(Tameable):
		_18_ocelot_type = Byte

	class Wolf(Tameable):
		_16_tameable_flags = Flags[Byte] (
			IS_SITTING	= 0x01,
			IS_ANGRY	= 0x02,
			IS_TAME	= 0x04,
		)
		_18_health = Float
		_19_begging = Byte
		_20_collar_color = Byte

	class Pig(Ageable):
		_16_has_saddle = Byte

	class Rabbit(Ageable):
		_18_rabbit_type = Byte

	class Sheep(Ageable):
		_16_sheep_style = Flags[Byte] (
			COLOR_WHITE		= 0x00,
			COLOR_ORANGE		= 0x01,
			COLOR_MAGENTA		= 0x02,
			COLOR_LIGHT_BLUE	= 0x03,
			COLOR_YELLOW		= 0x04,
			COLOR_LIME		= 0x05,
			COLOR_PINK		= 0x06,
			COLOR_GRAY		= 0x07,
			COLOR_SILVER		= 0x08,
			COLOR_CYAN		= 0x09,
			COLOR_PURPLE		= 0x0A,
			COLOR_BLUE		= 0x0B,
			COLOR_BROWN		= 0x0C,
			COLOR_GREEN		= 0x0D,
			COLOR_RED		= 0x0E,
			COLOR_BLACK		= 0x0F,
			IS_SHEARED		= 0x10,
		)

	class Villager(Ageable):
		_16_villager_type = Enum[Int] (
			FARMER		= 0,
			LIBRARIAN	= 1,
			PRIEST		= 2,
			BLACKSMITH	= 3,
			BUTCHER	= 4,
		)

	class Enderman(LivingEntity):
		_16_carried_block = Short
		_17_carried_block_data = Byte
		_18_is_screaming = Byte

	class Zombie(LivingEntity):
		_12_zombie_is_child = Byte
		_13_zombie_is_villager = Byte
		_14_zombie_is_converting = Byte

	class ZombiePigman(Zombie):
		pass

	class Blaze(LivingEntity):
		_16_blaze_on_fire = Byte

	class Spider(LivingEntity):
		_16_spider_is_climbing = Byte

	class CaveSpider(Spider):
		pass

	class Creeper(LivingEntity):
		_16_creeper_state = Enum[Byte] (
			IDLE = -1,
			FUSE = 1,
		)
		_17_creeper_is_powered = Byte

	class Ghast(LivingEntity):
		_16_ghast_is_attacking = Byte

	class Slime(LivingEntity):
		_16_slime_size = Byte

	class MagmaCube(Slime):
		pass

	class Skeleton(LivingEntity):
		_13_skeleton_type = Enum[Byte] (
			NORMAL = 0,
			WITHER = 1,
		)

	class Witch(LivingEntity):
		_21_witch_is_agressive = Byte

	class IronGolem(LivingEntity):
		_16_golem_is_player_created = Byte

	class Wither(LivingEntity):
		_17_wither_watched_target_1 = Int
		_18_wither_watched_target_2 = Int
		_19_wither_watched_target_3 = Int
		_20_wither_invulnerable_time = Int

	class Boat(Entity):
		_17_boat_time_since_hit = Int
		_18_boat_forward_direction = Int
		_19_boat_damage_taken = Float

	class Minecart(Entity):
		_17_minecart_shaking_power = Int
		_18_minecart_shaking_direction = Int
		_19_minecart_damage_taken = Float
		_20_minecart_block = Mask[Int] (
			BLOCK_ID	= 0x00FF,
			BLOCK_DATA	= 0xFF00,
		)
		_21_minecart_block_y = Int
		_22_minecart_show_block = Byte

	class FurnaceMinecart(Minecart):
		_16_furnaceminecart_is_powered = Bool

	class Item(Entity):
		_10_item = Slot

	class Arrow(Entity):
		_16_arrow_is_critical = Byte

	class Firework(Entity):
		_8_firework_info = Slot

	class ItemFrame(Entity):
		_2_itemframe_item = Slot
		_3_itemframe_rotation = Byte

	class EnderCrystal(Entity):
		_8_health = Int

	entity_types = allsubclasses(_EntityMetadataBase)
del position, look

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

S.EncryptionResponse = Packet(LOGIN, 0x01,
	server_id = String,
	key_length = Length[Short, 'key'],
	key = Array[Byte, 'key_length'],
	token_length = Length[Short, 'token'],
	token = Array[Byte, 'token_length'],
)


# Clientbound

C.LoginDisconnect = Packet(LOGIN, 0x00,
	reason = JSON,
)

C.EncryptionRequest = Packet(LOGIN, 0x01,
	key_length = Length[Short, 'key'],
	key = Array[Byte, 'key_length'],
	token_length = Length[Short, 'token'],
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
	mouse = Enum[Byte] (
		RIGHT	= 0,
		LEFT	= 1,
	),
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
		DIGGING_START		= 0,
		DIGGING_CANCEL		= 1,
		DIGGING_FINISH		= 2,
		DROP_ITEM_STACK	= 3,
		DROP_ITEM		= 4,
		ITEM_USAGE_FINISH	= 5,
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
		NONE			= 0,
		SWING_ARM		= 1,
		DAMAGE			= 2,
		LEAVE_BED		= 3,
		EAT_FOOD		= 5,
		CRITICAL_EFFECT	= 6,
		MAGIC_CRITICAL_EFFECT	= 7,
		CROUCH			= 104,
		UNCROUCH		= 105,
	),
)

S.EntityAction = Packet(PLAY, 0x0B,
	eid = Int,
	action = Enum[Byte] (
		CROUCH		= 1,
		UNCROUCH	= 2,
		LEAVE_BED	= 3,
		SPRINT_START	= 4,
		SPRINT_STOP	= 5,
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
	action = Short,
	mode = Byte,
	item = Slot,
)

S.ConfirmTransaction = Packet(PLAY, 0x0F,
	window_id = Byte,
	action = Short,
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
		CREATIVE_MODE	= 0x01,
		FLYING		= 0x02,
		ALLOW_FLYING	= 0x04,
		INVULNERABLE	= 0x08,
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
		FAR	= 0,
		NORMAL	= 1,
		SHORT	= 2,
		TINY	= 3,
	),
	chat_flags = Flags[Byte] (
		MODE_ENABLED		= 0b00,
		MODE_COMMANDS_ONLY	= 0b01,
		MODE_HIDDEN		= 0b10,
		COLORS			= 0b1000,
	),
	chat_colors = Bool,
	difficulty = Byte,
	show_cape = Bool,
)

S.ClientStatus = Packet(PLAY, 0x16,
	action = Enum[Byte] (
		RESPAWN			= 1,
		STATS_REQUEST			= 2,
		OPEN_INVENTORY_ACHIEVEMENT	= 3,
	),
)

S.PluginMessage = Packet(PLAY, 0x17,
	channel = String,
	length = Length[Short, 'data'],
	data = Array[Byte, 'length'],
)


# Clientbound

C.KeepAlive = Packet(PLAY, 0x00,
	keepalive_id = Int,
)

C.JoinGame = Packet(PLAY, 0x01,
	eid = Int,
	gamemode = Flags[UByte] (
		SURVIVAL	= 0,
		CREATIVE	= 1,
		ADVENTURE	= 2,
		HARDCORE	= 0x8,
	),
	dimension = Enum[Byte] (
		NETHER		= -1,
		OVERWORLD	= 0,
		END		= 1,
	),
	difficulty = Enum[UByte] (
		PEACEFUL	= 0,
		EASY		= 1,
		NORMAL		= 2,
		HARD		= 3,
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
		HELD		= 0,
		BOOTS		= 1,
		LEGGINGS	= 2,
		CHESTPLATE	= 3,
		HELMET		= 4,
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
		NETHER		= -1,
		OVERWORLD	= 0,
		END		= 1,
	),
	difficulty = Enum[UByte] (
		PEACEFUL	= 0,
		EASY		= 1,
		NORMAL		= 2,
		HARD		= 3,
	),
	gamemode = Enum[UByte] (
		SURVIVAL	= 0,
		CREATIVE	= 1,
		ADVENTURE	= 2,
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
		NONE			= 0,
		SWING_ARM		= 1,
		DAMAGE			= 2,
		LEAVE_BED		= 3,
		EAT_FOOD		= 5,
		CRITICAL_EFFECT	= 6,
		MAGIC_CRITICAL_EFFECT	= 7,
		CROUCH			= 104,
		UNCROUCH		= 105,
	),
)

C.SpawnPlayer = Packet(PLAY, 0x0C,
	eid = VarInt,
	uuid = String,
	name = String,
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
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
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
	pitch = Byte,
	yaw = Byte,
	data = Int, # https://wiki.vg/Object_Data
)

C.SpawnMob = Packet(PLAY, 0x0F, # TODO: https://wiki.vg/Entity_metadata#Objects
	eid = VarInt,
	type = Byte,
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
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
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
	count = Short,
)

C.EntityVelocity = Packet(PLAY, 0x12,
	eid = Int,
	dx = Short,
	dy = Short,
	dz = Short,
)

C.DestroyEntities = Packet(PLAY, 0x13,
	count = Length[Byte, 'eids'],
	eids = Array[Int, 'count'],
)

C.Entity = Packet(PLAY, 0x14,
	eid = Int,
)

C.EntityRelativeMove = Packet(PLAY, 0x15,
	eid = Int,
	dx = Fixed[Byte],
	dy = Fixed[Byte],
	dz = Fixed[Byte],
)

C.EntityLook = Packet(PLAY, 0x16,
	eid = Int,
	yaw = Byte,
	pitch = Byte,
)

C.EntityLookAndRelativeMove = Packet(PLAY, 0x17,
	eid = Int,
	dx = Fixed[Byte],
	dy = Fixed[Byte],
	dz = Fixed[Byte],
	yaw = Byte,
	pitch = Byte,
)

C.EntityTeleport = Packet(PLAY, 0x18,
	eid = Int,
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
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
		ENTITY_HURT			= 2,
		ENTITY_DEAD			= 3,
		WOLF_TAMING			= 6,
		WOLF_TAMED			= 7,
		WOLF_SHAKING			= 8,
		EATING_ACCEPTED		= 9,
		SHEEP_EATING			= 10,
		IRON_GOLEM_ROSE		= 11,
		VILLAGER_LOVES			= 12,
		VILLAGER_ANGRY			= 13,
		VILLAGER_HAPPY			= 14,
		WITCH_MAGIC			= 15,
		ZOMBIE_VILLAGER_HEALING	= 16,
		FIREWORK_EXPLODING		= 17,
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
	count = Length[Int, 'properties'],
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
	abm = UShort,
	size = Size[Int, 'data'],
	data = Zlibbed[Byte, 'size'],
)

C.MultiBlockChange = Packet(PLAY, 0x22,
	chunk_x = VarInt,
	chunk_z = VarInt,
	count = Length[Short, 'records'],
	size = Size[Int, 'records'],
	records = Array[Mask[UInt] (
		BLOCK_DATA	= 0x0000000F,
		BLOCK_ID	= 0x0000FFF0,
		BLOCK_Y	= 0x00FF0000,
		BLOCK_Z	= 0x0F000000,
		BLOCK_X	= 0xF0000000,
	), 'count'],
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
	count = Length[Short, 'meta'],
	size = Size[Int, 'data'],
	sky_light_sent = Bool,
	data = Zlibbed[Byte, 'size'],
	meta = Array[Struct (
		chunk_x = Int,
		chunk_z = Int,
		pbm = UShort,
		abm = UShort,
	), 'count'],
)

C.Explosion = Packet(PLAY, 0x27,
	x = Float,
	y = Float,
	z = Float,
	radius = Float,
	count = Length[Int, 'records'],
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
		MASTER		= 0,
		MUSIC		= 1,
		RECORDS	= 2,
		WEATHER	= 3,
		BLOCKS		= 4,
		MOBS		= 5,
		ANIMALS	= 6,
		PLAYERS	= 7,
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
		INVALID_BED		= 0,
		RAINING_BEGIN		= 1,
		RAINING_END		= 2,
		CHANGE_GAMEMODE	= 3,
		ENTER_CREDITS		= 4,
		DEMO_MESSAGE		= 5,
		BOW_HIT		= 6,
		FADE_VALUE		= 7,
		FADE_TIME		= 8,
	),
	value = Float,
)

C.SpawnGlobalEntity = Packet(PLAY, 0x2C,
	eid = VarInt,
	type = Enum[Byte] (
		THUNDERBOLT = 1,
	),
	x = Fixed[Int],
	y = Fixed[Int],
	z = Fixed[Int],
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
	count = Length[Short, 'slots'],
	slots = Array[Slot, 'count'],
)

C.WindowProperty = Packet(PLAY, 0x31,
	window_id = UByte,
	property = Enum[Short] (
		FURNACE_PROGRESS	= 0,
		FURNACE_FUEL		= 1,
	),
	value = Short,
)

C.ConfirmTransaction = Packet(PLAY, 0x32,
	window_id = UByte,
	action = Short,
	accepted = Bool,
)

C.UpdateSign = Packet(PLAY, 0x33,
	x = Int,
	y = Byte,
	z = Int,
	lines = Array[String, 4],
)

C.MapData = Packet(PLAY, 0x34, # TODO parse array
	item_damage = VarInt,
	length = Length[Short, 'data'],
	data = Array[Byte, 'length'],
)

C.UpdateBlockEntity = Packet(PLAY, 0x35,
	x = Int,
	y = Short,
	z = Int,
	action = Enum[UByte] (
		MOB_IN_SPAWNER = 1,
	),
	length = Length[Short, 'nbt_data'],
	nbt_data = Optional[NBT, 'length'],
)

C.SignEditorOpen = Packet(PLAY, 0x36,
	x = Int,
	y = Int,
	z = Int,
)

C.Statistics = Packet(PLAY, 0x37,
	count = Length[VarInt, 'data'],
	data = Array[Struct (
		name = String,
		amount = VarInt,
	), 'count'],
)

C.PlayerListItem = Packet(PLAY, 0x38,
	name = String,
	online = Bool,
	ping = Short,
)

C.PlayerAbilities = Packet(PLAY, 0x39,
	flags = Flags[Byte] (
		INVULNERABLE	= 0x01,
		FLYING		= 0x02,
		ALLOW_FLYING	= 0x04,
		CREATIVE_MODE	= 0x08,
	),
	flying_speed = Float,
	walking_speed = Float,
)

C.TabComplete = Packet(PLAY, 0x3A,
	count = Length[VarInt, 'matches'],
	matches = Array[String, 'count'],
)

C.ScoreboardObjective = Packet(PLAY, 0x3B,
	name = String,
	value = String,
	action = Enum[Byte] (
		CREATE = 0,
		REMOVE = 1,
		UPDATE = 2,
	),
)

C.UpdateScore = Packet(PLAY, 0x3C,
	name = String,
	action = Enum[Byte] (
		UPDATE = 0,
		REMOVE = 1,
	),
	score_name = String,
	value = Int,
)

C.DisplayScoreboard = Packet(PLAY, 0x3D,
	position = Enum[Byte] (
		LIST		= 0,
		SIDEBAR	= 1,
		BELOW_NAME	= 2,
	),
	score_name = String,
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
	count = Optional[Length[Short, 'players'], 'mode', (0, 3, 4)],
	players = Optional[Array[String, 'count'], 'mode', (0, 3, 4)],
)

C.PluginMessage = Packet(PLAY, 0x3F,
	channel = String,
	length = Length[Short, 'data'],
	data = Array[Byte, 'length'],
)

C.Disconnect = Packet(PLAY, 0x40,
	reason = Chat,
)

# TODO: replace all assertions with exceptions

# by Sdore, 2020
