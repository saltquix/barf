# -*- coding: utf-8 -*-
from saltquix.NesRom import NesRom
from saltquix.barf.RiverCityRansomTextEncoding import english, japanese
from saltquix.barf import chunks

class RiverCityRansomRom(NesRom):

  def __init__(self):
    NesRom.__init__(self)

  def load(self, path):
    NesRom.load(self, path)
    if self.checkJapaneseVersion():
      self.encoding = japanese
      self.model = {
        'npc_names': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=0, start=0x3D84, end=0x4000),
        'npc_dialog': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=1, start=0x20, end=0x14A5),
        'misc_text': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=3, start=0x30B5, end=0x3D13),
        'shop_dialog': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x1EA2, end=0x21EE),
        'shop_submenus': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x236C, end=0x23A7),
        'shop_names': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x1C85, end=0x1D04,
          count=24, base='data_start', ptr_OR=0, ptr_bytes=1)
      }
    else:
      self.encoding = english
      self.model = {
        'npc_names': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=0, start=0x3D48, end=0x4000),
        'npc_dialog': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=1, start=0x20, end=0x1C00),
        'misc_text': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=3, start=0x3200, end=0x3E00),
        'shop_dialog': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x1F46, end=0x21D2),
        'shop_submenus': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x2351, end=0x23E2),
        'shop_names': chunks.PointerDataBlock(chunks.TerminatedString, bank_type='prg', bank_number=2, start=0x1C0C, end=0x1DBE,
          count=24, base='data_start', ptr_OR=0)
      }

  @property
  def npcNames(self):
    return self.model['npc_names'].read(self)

  # arbitrary method... feel free to improve this
  def checkJapaneseVersion(self):
    prg7 = self.prg_banks[7]
    return prg7[0xAFD] != 0xE8 or prg7[0xAFE] != 0x8A or prg7[0xAFF] != 0x29
