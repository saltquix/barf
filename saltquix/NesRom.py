# -*- coding: utf-8 -*-
import struct, os, hashlib

class NesRom(object):

  def __init__(self):
    self.prg_banks = []
    self.chr_banks = []
    self.title_ = None

  @property
  def title(self):
    return self.title_
  @title.setter
  def title(self, value):
    if value != None:
      value = value.encode('us-ascii')
      if len(value) > 128:
        raise StandardError('title cannot be over 128 characters long')
      if value.find('\0') != -1:
        raise StandardError('title cannot contain embedded null characters')
    self.title_ = value

  def update_hash(self, hash):
    hash.update('NES\x1A')
    hash.update(bytearray( ( \
      len(self.prg_banks), len(self.chr_banks), \
      self.flags6, self.flags7, self.prg_ram_size, self.flags9, self.flags10, \
      0, 0, 0, 0, 0) ))
    for bank in self.prg_banks:
      hash.update(bank)
    for bank in self.chr_banks:
      hash.update(bank)
    return hash

  def md5(self):
    return self.update_hash(hashlib.new('md5')).hexdigest()

  def load(self, path):
    with open(path, 'rb') as f:
      try:
        if f.read(4) != 'NES\x1A':
          raise StandardError('not a valid iNES ROM image (file header not found)')
        (prg_count, chr_count) = struct.unpack('BB', f.read(2))
        (flags6, flags7, prg_ram_size, flags9, flags10) = struct.unpack('BBBBB', f.read(5))
        if f.read(5) != '\0\0\0\0\0':
          raise StandardError('not a valid iNES ROM image (file header padding)')
        prg_banks = []
        chr_banks = []
        for i in range(prg_count):
          prg_bank = bytearray(f.read(0x4000))
          if len(prg_bank) != 0x4000:
            raise EOFError()
          prg_banks.append(prg_bank)
        for i in range(chr_count):
          chr_bank = bytearray(f.read(0x2000))
          if len(chr_bank) != 0x2000:
            raise EOFError()
          chr_banks.append(chr_bank)
        title = f.read(128)
        cutoff = title.find('\0')
        if cutoff != 0:
          title = title[:cutoff]

        self.flags6 = flags6
        self.flags7 = flags7
        self.prg_ram_size = prg_ram_size
        self.flags9 = flags9
        self.flags10 = flags10
        self.prg_banks = prg_banks
        self.chr_banks = chr_banks
        self.title = title
      except (struct.error, EOFError):
        raise StandardError('invalid iNES ROM image (unexpected end of data)')

  def save(self, path):
    new_path = path+'._new_.nes'
    if os.path.exists(new_path):
      i = 2
      while os.path.exists('%s._new%d_.nes' % (path, i)):
        i += 1
      new_path = '%s._new%d_.nes' % (path, i)
    with open(new_path, 'wb') as f:
      f.write('NES\x1A')
      f.write(struct.pack('BB', len(self.prg_banks), len(self.chr_banks)))
      flags6 = self.flags6
      flags7 = self.flags7
      prg_ram_size = self.prg_ram_size
      flags9 = self.flags9
      flags10 = self.flags10
      f.write(struct.pack('BBBBB', flags6, flags7, prg_ram_size, flags9, flags10))
      f.write('\0\0\0\0\0')
      for prg_bank in self.prg_banks:
        f.write(prg_bank)
      for chr_bank in self.chr_banks:
        f.write(chr_bank)
      if self.title:
        title = self.title[:128]
        if len(title) < 128:
          title += '0' * (128 - len(title))
        f.write(title)
    old_path = path+'._old_.nes'
    if os.path.exists(old_path):
      i = 2
      while os.path.exists('%s._old%d_.nes' % (path, i)):
        i += 1
      old_path = '%s._old%d_.nes' % (path, i)
    os.rename(path, old_path)
    os.rename(new_path, path)
    try:
      os.remove(old_path)
    except:
      pass

  def getBank(self, bank_type, bank_number):
    if bank_type == 'prg':
      return self.prg_banks[bank_number]
    elif bank_type == 'chr':
      return self.chr_banks[bank_number]
    raise Exception('unknown bank: ' + bank_type)
