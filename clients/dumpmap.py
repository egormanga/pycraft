#!/usr/bin/python3
# PyCraft dumpmap client

from PIL import Image, ImageEnhance
from utils.nolog import *
from ..client import *
logstart('ChatClient')

class DumpmapClient(MCClient):
	handlers = Handlers(MCClient.handlers)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.world = World()

@DumpmapClient.handler(C.PlayerPositionAndLook)
def handlePlayerPositionAndLook(s, p):
	s.player.pos.update(
		x = p.x,
		head_y = p.y,
		z = p.z,
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)

@DumpmapClient.handler(C.ChunkData)
def handleChunkData(s, p):
	s.world[s.player.dimension].load(p.chunk_x, p.chunk_z, p.pbm, p.abm, p.data)

@DumpmapClient.handler(C.MapChunkBulk)
def handleMapChunkBulk(s, p):
	data = p.data
	for i in p.meta:
		s.world[s.player.dimension].load(i.chunk_x, i.chunk_z, i.pbm, i.abm, data, sky_light=p.sky_light_sent)
		data = data[int((1 + .5 + .5*p.sky_light_sent) * 16**3) * bin(i.pbm).count('1'):]

@apmain
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-name', metavar='username', default=ClientConfig.username)
def main(cargs):
	class config(ClientConfig):
		username = cargs.name

	client = Builder(DumpmapClient, config=config) \
		.connect((cargs.ip, cargs.port)) \
		.login() \
		.block(state=PLAY) \
		.build()

	p = Progress(32)
	while (True):
		try:
			client.handle()
			l = len(client.world[0].chunksec)
			p.print(l)
			if (l >= 32): break
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)
	del p

	#block_names = {v['protocol_id']: k for k, v in json.load(open(os.path.dirname(os.path.realpath(sys.argv[0]))+'/'+'registries.json'))['minecraft:block']['entries'].items()}
	block_names = {int(k): v for k, v in dict(re.fullmatch(r'([\d:]+)\ \#\ .*\ \(([\w:]+)\)', i.strip()).groups() for i in open(os.path.dirname(os.path.realpath(sys.argv[0]))+'/'+'blocks.txt')).items() if k.isdigit()}

	texture_path = os.path.dirname(os.path.realpath(sys.argv[0]))+'/blocks'
	@functools.lru_cache
	def get_texture(id):
		try: block_name = block_names[id].partition('minecraft:')[2]
		except KeyError: log(f"Unknown block id {block.id}", tm=None); return None
		if (not block_name): return None
		for i in (block_name, block_name+'_top', block_name+'_still'):
			try: return Image.open(f"{texture_path}/{i}.png").crop((0, 0, 16, 16))
			except FileNotFoundError: pass
		else: log(f"Missing texture for block {block_name}", tm=None)
		return None

	print(len(client.world[0].chunksec), 'chunks loaded')
	print('Position:', client.player.pos)

	n = 3
	img = Image.new('RGBA', (16*16*(n+1)*2, 16*16*(n+1)*2), (255, 255, 255, 255))

	cx, cz = map(int, (client.player.pos.x//16, client.player.pos.z//16))
	p = Progress((n*2+1)**2)
	for dcz in range(-n, n+1):
		for dcx in range(-n, n+1):
			p.print((n+dcz)*(n*2+1)+(n+dcx))
			try: cs = client.world[0].chunksec[cx+dcx, cz+dcz]
			except KeyError: continue
			for cy, c in cs.chunks.items():
				for (x, y, z), block in sorted(c.blocks.items(), key=lambda x: x[0][1]):
					if (not block): continue
					texture = get_texture(block.id)
					if (texture is None): continue
					try: img.alpha_composite(ImageEnhance.Brightness(texture).enhance((block.sky_light+1)/12), (((n+dcx)*16+x)*16, ((n+dcz)*16+z)*16))
					except ValueError as ex: logexception(ex)

	#img = img.resize((512, 512), resample=Image.NEAREST)
	img.show()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
