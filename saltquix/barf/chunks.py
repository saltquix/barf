import struct
from pprint import pprint

# RCR likes to store decimal numbers as hexadecimal sometimes (e.g. 0x36 means decimal 36)
def dec_as_hex(h):
  try:
    return int('%x' % h, 10)
  except:
    return 0

class DataChunk:
  def __init__(self, bank_type, bank_number, start, end=None, index=None):
    self.bank_type = bank_type
    self.bank_number = bank_number
    self.start = start
    self.end = end
    self.index = index
  def getBank(self, rom):
    return rom.getBank(self.bank_type, self.bank_number)

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
    if self.index != None and ((self.index < rom.firstRealShopItem) or (self.index > rom.lastRealShopItem)):
      return (('name',name),)

    cost = dec_as_hex(bank[pos]) + dec_as_hex(bank[pos+1]) * 100 + dec_as_hex(bank[pos+2]) * 10000
    pos += 3

    unknown, action1, action2 = struct.unpack('BBB', memview[pos:pos+3].tobytes())
    pos += 3

    statflags = struct.unpack('<H', memview[pos:pos+2].tobytes())[0]
    pos += 2

    stats = []
    if statflags & 0x0002:
      stats.append('SG+%d' % bank[pos])
      pos += 1
    if statflags & 0x0008:
      stats.append('DF+%d' % bank[pos])
      pos += 1
    if statflags & 0x0010:
      stats.append('TH+%d' % bank[pos])
      pos += 1
    if statflags & 0x0020:
      stats.append('WN+%d' % bank[pos])
      pos += 1
    if statflags & 0x0040:
      stats.append('K+%d' % bank[pos])
      pos += 1
    if statflags & 0x0080:
      stats.append('P+%d' % bank[pos])
      pos += 1
    if statflags & 0x0001:
      stats.append('WL+%d' % bank[pos])
      pos += 1
    if statflags & 0x8000:
      stats.append('SM+%d' % bank[pos])
      pos += 1

    if len(stats) == 0:
      stats = ()
    else:
      stats = (('stats', ' '.join(stats)),)

    return (('name',name),('cost',cost),('unknown',unknown),('action1',action1),('action2',action2)) + stats
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
