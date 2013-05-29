import struct
from pprint import pprint

class DataChunk:
  def __init__(self, bank_type, bank_number, start, end=None):
    self.bank_type = bank_type
    self.bank_number = bank_number
    self.start = start
    self.end = end
  def getBank(self, rom):
    return rom.getBank(self.bank_type, self.bank_number)

class TerminatedString(DataChunk):
  def __init__(self, bank_type, bank_number, start, terminator=0x05):
    DataChunk.__init__(self, bank_type, bank_number, start)
    self.terminator = terminator
  def read(self, rom):
    return rom.encoding.readterminated(self.getBank(rom), self.start, self.terminator)[0]
  def encode(self, rom, value):
    return rom.encoding.encode(value, self.terminator)

class PointerDataBlock(DataChunk):
  def __init__(self, data_type, bank_type, bank_number, start, end, ptr_OR=0x8000, count=None, base='bank_start', ptr_bytes=2):
    DataChunk.__init__(self, bank_type, bank_number, start, end)
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
        chunk = self.DataType(bank_type = self.bank_type, bank_number = self.bank_number, start = ptr)
        entry = chunk.read(rom)
        result.append(entry)
    return tuple(result)
  def write(self, rom, values):
    o = self.DataType(bank_type = self.bank_type, bank_number = self.bank_number, start=0)
    encoded = [(b'' if value == None else o.encode(rom, value)) for value in values]
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
