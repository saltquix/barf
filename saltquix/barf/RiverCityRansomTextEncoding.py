# -*- coding: utf-8 -*-
import codecs, pkgutil, StringIO, re, os, unicodedata
from pprint import pprint

class RiverCityRansomTextEncoding(object):

  def __init__(self):
    self.decodeMapping = [None for x in range(256)]
    self.currencySymbol = ''
    self.currencyDecimalPlaces = 0

  def formatCurrency(self, v):
    fmt = '%%s%%0.%df' % self.currencyDecimalPlaces
    return fmt % (self.currencySymbol, float(v) / 10**self.currencyDecimalPlaces)

  def load(self, path):
    f = codecs.open(path, 'r', 'utf-8')
    try:
      self.encodeMapping = {}
      encodeList = []
      for line in f:
        if re.match('^\s*(#.*)?$', line):
          continue
        parts = re.match('^\s*(?:(\d+)|(0x[a-fA-F0-9]+))\s*:\s*(\S.*?)\s*$', line)
        if not parts:
          parts = re.match(r'^\s*CURRENCY_SYMBOL\s*:\s*(?:<([^>]+)>|(\S.*?))\s*$', line)
          if parts:
            if parts.group(1):
              self.currencySymbol = unicodedata.lookup(parts.group(1))
            else:
              self.currencySymbol = parts.group(2)
            continue
          parts = re.match(r'^\s*CURRENCY_DECIMAL_PLACES\s*:\s*(\d+)\s*$', line)
          if parts:
            self.currencyDecimalPlaces = int(parts.group(1))
            continue
          raise Exception("invalid content in character mapping file")
        code, hex_code, mappings = parts.groups()
        if code:
          code = int(code)
        else:
          code = int(hex_code, 16)
        first = True
        for mapping in re.finditer('<([^>]+)>|(\S)', mappings):
          if mapping.group(1):
            mapping = unicodedata.lookup(mapping.group(1))
          else:
            mapping = mapping.group(2)
          if first:
            first = False
            self.decodeMapping[code] = mapping
          self.encodeMapping[mapping] = code
          encodeList.append(re.escape(mapping))
      encodeList.sort(key=lambda value:-len(value))
      self.encodePattern = re.compile('(?:(' + '|'.join(encodeList) + ')|(.))')
    finally:
      f.close()

  def readterminated(self, memview, pos, terminator=0x5):
    result = StringIO.StringIO()
    try:
      while memview[pos] != terminator:
        code = memview[pos]
        pos += 1
        character = self.decodeMapping[code]
        if character == None:
          raise Exception("unknown symbol: %02X" % code)
        result.write(character)
      return (result.getvalue(), pos + 1)
    finally:
      result.close()

  def encode(self, value, terminator = None):
    output = bytearray()
    for c in self.encodePattern.finditer(value):
      match = c.group(1)
      if not match:
        raise Exception("unsupported character found in text (" + unicodedata.name(c.group(2)) + ")")
      if match not in self.encodeMapping:
        raise Exception("internal error - mapping not found: " + match)
      output.append(self.encodeMapping[match])
    if terminator:
      output.append(terminator)
    return output

this_dir, this_filename = os.path.split(__file__)

english = RiverCityRansomTextEncoding()
english.load(os.path.join(this_dir, 'data', 'english.txt'))

japanese = RiverCityRansomTextEncoding()
japanese.load(os.path.join(this_dir, 'data', 'japanese.txt'))
