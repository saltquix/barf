import struct
from pprint import pprint

# RCR likes to store decimal numbers as hexadecimal sometimes (e.g. 0x36 means decimal 36)
def hex2dec(h):
  return int('%x' % h, 10)
def dec2hex(d):
  return int('%d' % d, 16)

class DataChunk:
  def __init__(self, bank_type, bank_number, start, end=None, index=None):
    self.bank_type = bank_type
    self.bank_number = bank_number
    self.start = start
    self.end = end
    self.index = index
  def getBank(self, rom):
    return rom.getBank(self.bank_type, self.bank_number)

class Bytes(DataChunk):
  def __init__(self, bank_type, bank_number, start, end, index=None):
    DataChunk.__init__(self, bank_type, bank_number, start, end, index=index)
  def read(self, rom):
    return tuple(self.getBank(rom)[self.start:self.end])
  def write(self, rom, values):
    self.getBank(rom)[self.start:self.end] = values

class TerminatedBytes(DataChunk):
  def __init__(self, bank_type, bank_number, start, terminator=0xFF, index=None):
    DataChunk.__init__(self, bank_type, bank_number, start, index=index)
    self.terminator = terminator
  def read(self, rom):
    bank = self.getBank(rom)
    values = []
    pos = self.start
    while bank[pos] != self.terminator:
      values.append(bank[pos])
      pos += 1
    return tuple(values)
  def encode(self, rom, values):
    return bytestring(values) + bytestring(self.terminator)

class DecAsHexCouplets(DataChunk):
  def __init__(self, bank_type, bank_number, start, end, index=None):
    if (end-start)%2 != 0:
      raise Exception("length of block must be divisible by 2")
    self.count = (end-start)/2
    DataChunk.__init__(self, bank_type, bank_number, start, end, index=index)
  def read(self, rom):
    bank = self.getBank(rom)
    values = []
    for pos in range(self.start, self.end, 2):
      values.append(hex2dec(bank[pos]) + hex2dec(bank[pos+1])*100)
    return tuple(values)
  def write(self, rom, values):
    if len(values) != self.count:
      raise Exception("expected %d values, got %d" % (self.count, len(values)))
    bank = self.getBank(rom)
    for i,v in enumerate(values):
      if v > 9999:
        raise Exception("maximum value 9999 exceeded")
      pos = self.start + i*2
      bank[pos] = dec2hex(v % 100)
      bank[pos+1] = dec2hex((v / 100) % 100)

class DecAsHexTriplets(DataChunk):
  def __init__(self, bank_type, bank_number, start, end, index=None):
    if (end-start)%3 != 0:
      raise Exception("length of block must be divisible by 3")
    self.count = (end-start)/3
    DataChunk.__init__(self, bank_type, bank_number, start, end, index=index)
  def read(self, rom):
    bank = self.getBank(rom)
    values = []
    for pos in range(self.start, self.end, 3):
      values.append(hex2dec(bank[pos]) + hex2dec(bank[pos+1])*100 + hex2dec(bank[pos+2])*10000)
    return tuple(values)
  def write(self, rom, values):
    if len(values) != self.count:
      raise Exception("expected %d values, got %d" % (self.count, len(values)))
    bank = self.getBank(rom)
    for i,v in enumerate(values):
      if v > 999999:
        raise Exception("maximum value 999999 exceeded")
      pos = self.start + i*3
      bank[pos] = dec2hex(v % 100)
      bank[pos+1] = dec2hex((v / 100) % 100)
      bank[pos+2] = dec2hex((v / 10000) % 100)

class TerminatedDecAsHex(DataChunk):
  def __init__(self, bank_type, bank_number, start, terminator=99, index=None):
    DataChunk.__init__(self, bank_type, bank_number, start, index=index)
    self.terminator = dec2hex(terminator)
  def read(self, rom):
    values = []
    bank = self.getBank(rom)
    pos = self.start
    while bank[pos] != self.terminator:
      values.append(hex2dec(bank[pos]))
      pos += 1
    return tuple(values)
  def encode(self, rom, values):
    return bytearray( tuple(dec2hex(v) for v in values) + (self.terminator,) )

class TerminatedString(DataChunk):
  def __init__(self, bank_type, bank_number, start, index=None, terminator=0x05):
    DataChunk.__init__(self, bank_type, bank_number, start, index=index)
    self.terminator = terminator
  def read(self, rom):
    return rom.encoding.readterminated(self.getBank(rom), self.start, self.terminator)[0]
  def encode(self, rom, value):
    return rom.encoding.encode(value, self.terminator)

class ShopItem(DataChunk):
  def __init__(self, bank_type, bank_number, start, index=None, terminator=0x05):
    DataChunk.__init__(self, bank_type, bank_number, start, index=index)
    self.terminator = terminator
  def read(self, rom):
    bank = self.getBank(rom)
    memview = memoryview(bank)
    name, pos = rom.encoding.readterminated(bank, self.start, self.terminator)

    try:
      cost = hex2dec(bank[pos]) + hex2dec(bank[pos+1]) * 100 + hex2dec(bank[pos+2]) * 10000
    except:
      cost = None
    pos += 3

    unknown, action1, action2 = struct.unpack('BBB', memview[pos:pos+3].tobytes())
    pos += 3

    statflags = struct.unpack('<H', memview[pos:pos+2].tobytes())[0]
    pos += 2

    stats = []
    if statflags & 0x0002 and bank[pos] != 0:
      stats.append('SG+%d' % bank[pos])
      pos += 1
    if statflags & 0x0008 and bank[pos] != 0:
      stats.append('DF+%d' % bank[pos])
      pos += 1
    if statflags & 0x0010 and bank[pos] != 0:
      stats.append('TH+%d' % bank[pos])
      pos += 1
    if statflags & 0x0020 and bank[pos] != 0:
      stats.append('WN+%d' % bank[pos])
      pos += 1
    if statflags & 0x0040 and bank[pos] != 0:
      stats.append('K+%d' % bank[pos])
      pos += 1
    if statflags & 0x0080 and bank[pos] != 0:
      stats.append('P+%d' % bank[pos])
      pos += 1
    if statflags & 0x0001 and bank[pos] != 0:
      stats.append('WL+%d' % bank[pos])
      pos += 1
    if statflags & 0x8000 and bank[pos] != 0:
      stats.append('SM+%d' % bank[pos])
      pos += 1

    if len(stats) == 0:
      stats = ()
    else:
      stats = (('stats', ' '.join(stats)),)

    if cost == None:
      cost = ()
    else:
      cost = (('cost', cost),)

    if action2 == 255:
      action2 = ()
    else:
      action2 = (('action2',action2),)

    return (('name',name),('unknown',unknown),('action1',action1)) + action2 + stats + cost
  def encode(self, rom, value):
    value = dict(value)
    encoded = rom.encoding.encode(value['name'], self.terminator)
    return encoded

class PointerDataBlock(DataChunk):
  def __init__(self, data_type, bank_type, bank_number, start, end, index=None, ptr_OR=0x8000, count=None, base='bank_start', ptr_bytes=2):
    DataChunk.__init__(self, bank_type, bank_number, start, end, index=index)
    self.DataType = data_type
    self.ptr_OR = ptr_OR
    self.base = base
    self.count = count
    self.ptr_bytes = ptr_bytes
  def read(self, rom):
    bank = self.getBank(rom)
    result = []
    if self.count != None:
      data_start = self.start + (self.count * self.ptr_bytes)
    else:
      data_start = self.end
    memview = memoryview(bank)
    if self.base == 'data_start':
      base = data_start
    else:
      base = 0
    for i in range(self.start, self.end, self.ptr_bytes):
      if i >= data_start:
        break
      if self.ptr_bytes == 1:
        ptr = bank[i]
      else:
        ptr = struct.unpack('<H', memview[i:i+2].tobytes())[0]
      if self.ptr_OR != 0 and ptr == 0:
        result.append(None)
      else:
        ptr = (ptr & 0x3FFF) + base
        data_start = min(data_start, ptr)
        entry = self.temp(start=ptr, index=(i - self.start) / self.ptr_bytes).read(rom)
        result.append(entry)
    return tuple(result)
  def temp(self, start=0, index=None):
    return self.DataType(bank_type = self.bank_type, bank_number=self.bank_number, start=start, index=index)
  def write(self, rom, values):
    values = tuple(values)
    while len(values)>0 and values[-1] == None:
      values = values[:-1]
    encoded = [(b'' if value == None else self.temp(index=i).encode(rom, value)) for i, value in enumerate(values)]
    ptrs = bytearray(len(values) * self.ptr_bytes)
    data = bytearray()
    entries = {}
    if self.base == 'data_start':
      base = 0
    else:
      base = self.start + 2*len(values)
    for i in sorted([i for i in range(len(encoded))], key=lambda i: -len(encoded[i])):
      if values[i] == None:
        if self.ptr_bytes == 1:
          ptrs[i] = '\0'
        else:
          ptrs[i*2:i*2 + 2] = '\0\0'
        continue
      enc = encoded[i]
      context = entries
      addme = False
      for j in reversed(range(len(enc))):
        enc_j = enc[j]
        if enc_j in context:
          context = context[enc_j]
        else:
          new_context = {"addr":base+j}
          context[enc_j] = new_context
          context = new_context
          addme = True
      if self.ptr_bytes == 1:
        ptrs[i] = context['addr']
      else:
        ptrs[i*2:i*2 + 2] = struct.pack('<H', context['addr'] | self.ptr_OR)
      if addme:
        data.extend(enc)
        base += len(enc)
    data_size = len(ptrs) + len(data)
    available_space = (self.end - self.start)
    overflow = data_size - available_space
    if overflow > 0:
      raise Exception("Data won't fit into available space! Need to free up at least %d byte%s." % (overflow, 's' if overflow != 1 else ''))
    self.getBank(rom)[self.start:self.start + data_size] = ptrs + data

class EntrancePointCollection(DataChunk):
  def __init__(self, bank_type, bank_number, start, end, index=None, ptr_OR=0x8000, count=None):
    DataChunk.__init__(self, bank_type, bank_number, start, end, index)
  def read(self, rom):
    bank = self.getBank(rom)
    memview = memoryview(bank)
    pos = self.start
    data_start = self.end
    points = []
    while pos < data_start:
      loc, cameraPosAddr, playerPosAddr = struct.unpack('<BHH', memview[pos:pos+5].tobytes())
      cameraPosAddr &= 0x3FFF
      playerPosAddr &= 0x3FFF
      cameraPos = struct.unpack('<H', memview[cameraPosAddr:cameraPosAddr+2].tobytes())[0]
      player1_x, player1_y, elevation, player2_x, player2_y = struct.unpack('<HBBBB', memview[playerPosAddr:playerPosAddr+6].tobytes())
      player2_x |= player1_x & 0xFF00
      data_start = min(data_start, cameraPosAddr, playerPosAddr)
      point = ()
      point += (('camera_left', cameraPos),)
      point += (('player1_left', player1_x),)
      point += (('player1_top', player1_y),)
      point += (('player2_left', player2_x),)
      point += (('player2_top', player2_y),)
      if elevation != 0:
        point += (('elevation', elevation),)
      points.append( (loc, point) )
      pos += 5
    return tuple(points)

class ExitZoneCollection(DataChunk):
  def __init__(self, bank_type, bank_number, start, end, index=None, ptr_OR=0x8000, count=None):
    DataChunk.__init__(self, bank_type, bank_number, start, end, index)
  def read(self, rom):
    bank = self.getBank(rom)
    memview = memoryview(bank)
    pos = self.start
    data_start = self.end
    allLocationZones = []
    while pos < data_start:
      zonesPos = struct.unpack('<H', memview[pos:pos+2].tobytes())[0]
      zonesPos &= 0x3FFF
      data_start = min(data_start, zonesPos)
      locationZones = []
      while True:
        zonePos = struct.unpack('<H', memview[zonesPos:zonesPos+2].tobytes())[0]
        if zonePos == 0:
          break
        zonePos &= 0x3FFF
        flags, target_id, start_x, end_x, start_y, end_y = struct.unpack('<BBhhBB', memview[zonePos:zonePos+8].tobytes())
        target_type = 'shop' if flags&0x80 else 'location'
        door = struct.unpack('<H', memview[zonePos+8:zonePos+10].tobytes())[0] if flags&0x40 else None
        locationZone = ()
        locationZone += (('target_type', target_type),)
        locationZone += (('target_id', target_id),)
        locationZone += (('start_x', start_x),)
        locationZone += (('end_x', end_x),)
        locationZone += (('start_y', start_y),)
        locationZone += (('end_y', end_y),)
        if door:
          locationZone += (('door', door),)
        locationZone += (('flags', flags & 0x3F),)
        locationZones.append(locationZone)
        zonesPos += 2
      allLocationZones.append(tuple(locationZones))
      pos += 2
    return tuple(allLocationZones)
