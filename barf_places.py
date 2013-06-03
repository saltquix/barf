#!/usr/bin/python
import sys, codecs, os, platform, ConfigParser, re, itertools
from saltquix import barf
from saltquix.barf import Hackery
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

def point_to_string(pair):
  point = dict(pair[1])
  s = 'location %d (player1: %d,%d) (player2: %d,%d) (camera: %d)' % ( \
      pair[0], \
      point['player1_left'], point['player1_top'], point['player2_left'], point['player2_top'], point['camera_left'])
  if 'elevation' in point:
    s += ' (elevation: {0})'.format(point['elevation'])
  return s

def run():
  with Hackery(places="places.txt") as hackery:
    rom = hackery.rom
    if hackery.action == 'saveback':
      name_codes = [0 for i in range(35)]
      pacifist_mode = [0 for i in range(35)]
      reincarnation = [0 for i in range(35)]
      music_tracks = [0 for i in range(35)]
      no_probability = tuple(0 for i in range(9))
      gang_probability = [None for i in range(35)]
      with hackery.opentxt('places', 'r') as f:
        current_id = None
        for l in f:
          if re.match(r'^\s*(#.*)?$', l):
            continue
          set_id = re.match(r'^\s*(\d+)\s*\.\s*(#.*)?$', l)
          if set_id:
            set_id = int(set_id.group(1))
            if set_id >= len(name_codes):
              raise Exception("invalid place ID: %d" % set_id)
            current_id = set_id
            continue
          pair = re.match(r'^\s*([^\s:]+)\s*:\s*(.*)$', l)
          if pair == None:
            raise Exception('invalid content in places.txt')
          if current_id == None:
            raise Exception('you must specify a place ID number before setting values')
          key, value = pair.groups()
          if key == 'name_code':
            name_codes[current_id] = parse_num(key, value, True)
          elif key == 'reincarnation_location':
            reincarnation[current_id] = parse_num(key, value, False)
          elif key == 'music_track':
            music_tracks[current_id] = parse_num(key, value, True)
          elif key == 'pacifist_mode':
            pacifist_mode[current_id] = parse_onoff(key, value)
          elif key == 'gang_probability':
            gp = [0 for i in range(9)]
            for i, prob in enumerate(int(m.group(1)) for m in re.finditer('(\d+)%', value)):
              if i >= len(gp):
                raise Exception("gang_probability for location #%d: too many values" % current_id)
              if prob > 98:
                raise Exception("gang_probability for location #%d gang #%d: maximum value is 98%" % (current_id, i))
              gp[i] = prob
            gp = tuple(gp)
            while len(gp)>0 and gp[-1] == 0:
              gp = gp[:-1]
            if sum(gp) > 100:
              raise Exception("gang_probability for location #%d: total exceeds 100%%" % current_id)
            if len(gp) == 0:
              gp = None
            gang_probability[current_id] = gp
          else:
            raise Exception('unrecognised value: %s' % key)
      rom.model['location_name_codes'].write(rom, name_codes)
      rom.model['location_pacifist_mode'].write(rom, pacifist_mode)
      rom.model['reincarnation_locations'].write(rom, reincarnation)
      rom.model['location_music_tracks'].write(rom, music_tracks)
      with hackery.phase('packing gang probability data'):
        rom.model['location_gang_probability'].write(rom, gang_probability)
      hackery.finishsaveback()
    else:
      name_codes = rom.model['location_name_codes'].read(rom)
      reincarnation = rom.model['reincarnation_locations'].read(rom)
      music_tracks = rom.model['location_music_tracks'].read(rom)
      pacifist_mode = rom.model['location_pacifist_mode'].read(rom)
      gang_probability = rom.model['location_gang_probability'].read(rom)
      entry_points = rom.model['location_entry_points'].read(rom)
      entry_point_locs = (p[0] for p in entry_points)
      exit_zones = rom.model['location_exit_zones'].read(rom)
      with hackery.opentxt('places', 'w') as f:
        f.write('# name_code = line numbers from >>misc_text.txt<<%s' % os.linesep)
        f.write(os.linesep)
        f.write('##game_start: %s%s' % (point_to_string(entry_points[0]), os.linesep))
        f.write(os.linesep)
        for i in range(len(name_codes)):
          f.write('%d.%s' % (i, os.linesep))
          if i < len(name_codes):
            if name_codes[i] == 0:
              f.write(' name_code: (none)%s' % os.linesep)
            else:
              f.write(' name_code: %s%s' % (name_codes[i], os.linesep))
          if i < len(reincarnation):
            f.write(' reincarnation_location: %d%s' % (reincarnation[i], os.linesep))
            target_point_id = reincarnation[i]
            if target_point_id == 0:
              f.write(' ##reincarnation_point: game_start%s' % os.linesep)
            else:
              target_point = entry_points[target_point_id]
              from_loc = None
              to_loc = target_point[0]
              for loc, zones in enumerate(exit_zones):
                zones = (dict(zone) for zone in zones)
                if sum(1 for z in zones if z['target_type'] == 'location' and z['target_id'] == to_loc) == 1:
                  from_loc = loc
                  break
              if from_loc != None:
                f.write(' ##reincarnation_point: [location %d -> location %d]%s' % (from_loc, to_loc, os.linesep))
              else:
                f.write(' ##reincarnation_point: %s%s' % (point_to_string(target_point), os.linesep))
          if i < len(music_tracks):
            f.write(' music_track: %d%s' % (music_tracks[i], os.linesep))
          if i < len(pacifist_mode):
            f.write(' pacifist_mode: %s%s' % ('off' if pacifist_mode[i] == 0 else 'on', os.linesep))
          gp = () if (i >= len(gang_probability) or gang_probability[i] == None) else gang_probability[i]
          gp += tuple(0 for i in range(9 - len(gp)))
          gp = gp[:9]
          f.write(' gang_probability: %s%s' % (' '.join('%d%%'%v for v in gp), os.linesep))
          if i < len(exit_zones):
            f.write(' ##exits:%s' % os.linesep)
            for zone in exit_zones[i]:
              zone = dict(zone)
              target_id = zone['target_id']
              f.write(' ## [%d,%d,%d,%d]' % ( \
                zone['start_x'], zone['start_y'], \
                zone['end_x'], zone['end_y']))
              if 'door' in zone:
                f.write(' (door: %d)' % zone['door'])
              f.write(' (flags: %x)' % zone['flags'])
              if zone['target_type'] == 'location':
                f.write(' -> %s' % point_to_string(entry_points[target_id]))
              else:
                f.write(' -> %s %d' % (zone['target_type'], target_id))
              f.write(os.linesep)
          f.write(os.linesep)
      hackery.finishexport()

if __name__ == '__main__':
  try:
    run()
  except barf.Cancellation:
    pass
