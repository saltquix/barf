#!/usr/bin/python
import sys, codecs, os, platform, ConfigParser, re
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
  if len(sys.argv) >= 2:
    gfx_mode = False
    rom_path = sys.argv[1]
  else:
    import Tkinter, tkFileDialog
    gfx_mode = True
    root = Tkinter.Tk()
    root.withdraw()
    barf.setTkIcon(root)
    cfg = ConfigParser.ConfigParser()
    cfg.read('barf.cfg')
    if cfg.has_option('Paths', 'ROMs'):
      rom_folder = cfg.get('Paths', 'ROMs')
    else:
      rom_folder = os.path.split(__file__)[0]
    rom_path = tkFileDialog.askopenfilename(
      title = 'Please choose a River City Ransom ROM image file',
      filetypes = [('NES ROMs', '*.nes'), ('All files', '*.*')],
      initialdir = rom_folder)
    if not rom_path:
      return
    if not cfg.has_section('Paths'):
      cfg.add_section('Paths')
    cfg.set('Paths', 'ROMs', os.path.split(rom_path)[0])
    with open('barf.cfg', 'wb') as cfgfile:
      cfg.write(cfgfile)
  error_context = None
  try:
    rom = RiverCityRansomRom()
    rom.load(rom_path)
    output_folder = 'output'
    if len(sys.argv) >= 3:
      output_folder = sys.argv[2]
    if gfx_mode:
      cfg = ConfigParser.ConfigParser()
      cfg.read('barf.cfg')
      if cfg.has_option('Paths', 'Output'):
        output_folder = cfg.get('Paths', 'Output')
      output_folder = tkFileDialog.askdirectory(
        title = 'Please choose a data directory',
        initialdir = output_folder,
        mustexist = True)
      if not output_folder:
        return
      if not cfg.has_section('Paths'):
        cfg.add_section('Paths')
      cfg.set('Paths', 'Output', output_folder)
      with open('barf.cfg', 'wb') as cfgfile:
        cfg.write(cfgfile)
    elif not os.path.exists(output_folder):
      os.makedirs(output_folder)
    output_exists = os.path.exists(os.path.join(output_folder, 'places.txt'))
    action = 'extract'
    if output_exists:
      if gfx_mode:
        import tkMessageBox
        action = tkMessageBox.askquestion(
          'Save back changes?',
          'There are data files in this folder. Do you want to save data from these files back onto the ROM?\n\n'
          + 'Click "Yes" to save changed data files back to the ROM.\n'
          + 'Click "No" to overwrite the data files.\n'
          + 'Click "Cancel" to do nothing.',
          type = tkMessageBox.YESNOCANCEL)
        if action == 'yes':
          action = 'saveback'
        elif action == 'no':
          action = 'extract'
        else:
          action = None
    if action == 'extract':
      with codecs.open(os.path.join(output_folder, 'places.txt'), 'w', 'utf-8') as f:
        if platform.system() == 'Windows':
          # add BOM. screw the whiners
          f.write(u'\uFEFF')
        f.write('# name_code = line numbers from >>misc_text.txt<<%s' % os.linesep)
        f.write(os.linesep)
        name_codes = rom.model['location_name_codes'].read(rom)
        reincarnation = rom.model['reincarnation_locations'].read(rom)
        music_tracks = rom.model['location_music_tracks'].read(rom)
        pacifist_mode = rom.model['location_pacifist_mode'].read(rom)
        gang_probability = rom.model['location_gang_probability'].read(rom)
        for i in range(len(name_codes)):
          f.write('%d.%s' % (i, os.linesep))
          if i < len(name_codes):
            if name_codes[i] == 0:
              f.write(' name_code: (none)%s' % os.linesep)
            else:
              f.write(' name_code: %s%s' % (name_codes[i], os.linesep))
          if i < len(reincarnation):
            f.write(' reincarnation_location: %d%s' % (reincarnation[i], os.linesep))
          if i < len(music_tracks):
            f.write(' music_track: %d%s' % (music_tracks[i], os.linesep))
          if i < len(pacifist_mode):
            f.write(' pacifist_mode: %s%s' % ('off' if pacifist_mode[i] == 0 else 'on', os.linesep))
          gp = () if (i >= len(gang_probability) or gang_probability[i] == None) else gang_probability[i]
          gp += tuple(0 for i in range(9 - len(gp)))
          gp = gp[:9]
          f.write(' gang_probability: %s%s' % (' '.join('%d%%'%v for v in gp), os.linesep))
          f.write(os.linesep)
      message = 'Finished data export to ' + output_folder
      if gfx_mode:
        import tkMessageBox
        tkMessageBox.showinfo('Finished', message)
      else:
        print message
    elif action == 'saveback':
      name_codes = [0 for i in range(35)]
      pacifist_mode = [0 for i in range(35)]
      reincarnation = [0 for i in range(35)]
      music_tracks = [0 for i in range(35)]
      no_probability = tuple(0 for i in range(9))
      gang_probability = [None for i in range(35)]
      with codecs.open(os.path.join(output_folder, 'places.txt'), 'r', 'utf-8') as f:
        if f.read(1) != u'\uFEFF':
          f.seek(0)
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
          pair = re.match('^\s*([^\s:]+)\s*:\s*(.*)$', l)
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
      error_context = 'packing gang probability data'
      rom.model['location_gang_probability'].write(rom, gang_probability)
      rom.save(rom_path)
      message = 'Finished data import from ' + output_folder + '\ninto ' + rom_path
      if gfx_mode:
        import tkMessageBox
        tkMessageBox.showinfo('Finished', message)
      else:
        print message
  except Exception, e:
    if gfx_mode:
      import tkMessageBox
      tkMessageBox.showerror('Error %s' % (error_context or ''), 'Oops! An error occurred %s:\n\n%s' % (error_context or '', unicode(e)))
    raise
    

if __name__ == '__main__':
  run()
