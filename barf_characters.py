#!/usr/bin/python
import sys, codecs, os, platform, ConfigParser, re, itertools
from saltquix.barf.chunks import Stats
from saltquix import barf
from saltquix.barf.RiverCityRansomRom import RiverCityRansomRom
from saltquix.barf import chunks
from pprint import pprint
from glob import iglob
import logging
logging.basicConfig(filename='barf.log', level=logging.DEBUG)

def parse_num(name, value, none_okay):
  if none_okay and re.match('^\s*\(none\)', value):
    return 0
  m = re.match('^\s*(\d+)', value)
  if m == None:
    raise Exception("invalid value for %s: %s" % (name, value))
  return int(m.group(1))

def parse_onoff(name, value):
  if re.match('^\s*on\s*$', value):
    return 1
  if re.match('^\s*off\s*$', value):
    return 0
  raise Exception("invalid value for %s: %s" % (name, value))

def run():
  with barf.Hackery(gangs='gangs.txt', bosses='bosses.txt') as hackery:
    rom = hackery.rom
    if hackery.action == 'extract':
      turf_codes = rom.model['gang_turf_title_codes'].read(rom)
      if 'gang_cash' in rom.model:
        gang_cash = rom.model['gang_cash'].read(rom)
      else:
        gang_cash = ()
      if 'boss_cash' in rom.model:
        boss_cash = rom.model['boss_cash'].read(rom)
      else:
        boss_cash = ()
      boss_stats = rom.model['boss_stats'].read(rom)
      with hackery.opentxt('gangs', 'w') as f:
        f.write('# turf_code = line number from >>npc_dialog.txt<<%s' % os.linesep)
        f.write(os.linesep)
        for i in range(len(turf_codes)):
          f.write('%d.%s' % (i, os.linesep))
          if i < len(turf_codes):
            f.write(' turf_code: %s%s' % (turf_codes[i], os.linesep))
          if i < len(gang_cash):
            f.write(' cash: %s%s' % (rom.encoding.formatCurrency(gang_cash[i]), os.linesep))
          f.write(os.linesep)
      with hackery.opentxt('bosses', 'w') as f:
        for i in range(len(boss_stats)):
          f.write('%d.%s' % (i, os.linesep))
          if i < len(boss_cash):
            f.write(' cash: %s%s' % (rom.encoding.formatCurrency(boss_cash[i]), os.linesep))
          if i < len(boss_stats):
            for j, stat in enumerate(Stats._fields):
              f.write(' %s: %d%s' % (stat, boss_stats[i][j], os.linesep))
          f.write(os.linesep)
      hackery.finishexport()
    elif hackery.action == 'saveback':
      turf_codes = [0 for i in range(9)]
      gang_cash = [0 for i in range(9)]
      if 'boss_cash' in rom.model:
        boss_cash = list(rom.model['boss_cash'].read(rom))
      else:
        boss_cash = list()
      boss_stats = [{statName:stats[i] for i, statName in enumerate(Stats._fields)} for stats in rom.model['boss_stats'].read(rom)]
      print(boss_stats)
      with hackery.opentxt('gangs', 'r') as f:
        current_id = None
        for l in f:
          if re.match(r'^\s*(#.*)?$', l):
            continue
          set_id = re.match(r'^\s*(\d+)\s*\.\s*(#.*)?$', l)
          if set_id:
            set_id = int(set_id.group(1))
            if set_id >= len(turf_codes):
              raise Exception("invalid gang ID: %d" % set_id)
            current_id = set_id
            continue
          pair = re.match('^\s*([^\s:]+)\s*:\s*(.*)$', l)
          if pair == None:
            raise Exception('invalid content in gangs.txt')
          if current_id == None:
            raise Exception('you must specify a gang ID number before setting values')
          key, value = pair.groups()
          if key == 'turf_code':
            turf_codes[current_id] = parse_num(key, value, False)
          elif key == 'cash':
            gang_cash[current_id] = parse_num(key, re.sub(r'\D+', '', value), False)
          else:
            raise Exception('unrecognised value: %s' % key)
      with hackery.opentxt('bosses', 'r') as f:
        current_id = None
        for l in f:
          if re.match(r'^\s*(#.*)?$', l):
            continue
          set_id = re.match(r'^\s*(\d+)\s*\.\s*(#.*)?$', l)
          if set_id:
            set_id = int(set_id.group(1))
            if set_id >= len(boss_stats):
              raise Exception("invalid boss ID: %d" % set_id)
            current_id = set_id
            continue
          pair = re.match('^\s*([^\s:]+)\s*:\s*(.*)$', l)
          if pair == None:
            raise Exception('invalid content in boss.txt')
          if current_id == None:
            raise Exception('you must specify a gang ID number before setting values')
          key, value = pair.groups()
          if key == 'cash':
            boss_cash[current_id] = parse_num(key, re.sub(r'\D+', '', value), False)
          elif key == 'punch':
            boss_stats[current_id]['punch'] = parse_num(key, value, False)
          elif key == 'kick':
            boss_stats[current_id]['kick'] = parse_num(key, value, False)
          elif key == 'weapon':
            boss_stats[current_id]['weapon'] = parse_num(key, value, False)
          elif key == 'throw':
            boss_stats[current_id]['throw'] = parse_num(key, value, False)
          elif key == 'agility':
            boss_stats[current_id]['agility'] = parse_num(key, value, False)
          elif key == 'defence':
            boss_stats[current_id]['defence'] = parse_num(key, value, False)
          elif key == 'strength':
            boss_stats[current_id]['strength'] = parse_num(key, value, False)
          elif key == 'willpower':
            boss_stats[current_id]['willpower'] = parse_num(key, value, False)
          elif key == 'stamina':
            boss_stats[current_id]['stamina'] = parse_num(key, value, False)
          else:
            raise Exception('unrecognised value: %s' % key)
      boss_stats = tuple(Stats(**stats) for stats in boss_stats)
      rom.model['boss_stats'].write(rom, boss_stats)
      rom.model['gang_turf_title_codes'].write(rom, turf_codes)
      if 'gang_cash' in rom.model:
        rom.model['gang_cash'].write(rom, gang_cash)
      hackery.finishsaveback()
    
if __name__ == '__main__':
  try:
    run()
  except barf.Cancellation:
    pass
