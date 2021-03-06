#!/usr/bin/python
import sys, codecs, os, platform, ConfigParser, re
from saltquix import barf
from saltquix.barf.RiverCityRansomRom import RiverCityRansomRom
from saltquix.barf import chunks
from pprint import pprint

def writeLines(path, lines):
  f = codecs.open(path, 'w', 'utf-8')
  if platform.system() == 'Windows':
    # add BOM. screw the whiners
    f.write(u'\uFEFF')
  try:
    for i, el in enumerate(lines):
      if el == None:
        f.write(u'# (%d:--unused--)%s' % (i, os.linesep))
      else:
        f.write(u'%d:%s%s' % (i, el, os.linesep))
  finally:
    f.close()

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
    output_exists = False
    for key, o in rom.model.items():
      output_filepath = os.path.join(output_folder, '%s.txt' % key)
      if os.path.exists(output_filepath):
        if isinstance(o, chunks.PointerDataBlock) and o.DataType == chunks.TerminatedString:
          output_exists = True
          break
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
      for key, o in rom.model.items():
        output_filepath = os.path.join(output_folder, '%s.txt' % key)
        if isinstance(o, chunks.PointerDataBlock) and o.DataType == chunks.TerminatedString:
          writeLines(output_filepath, o.read(rom))
      message = 'Finished data export to ' + output_folder
      if gfx_mode:
        import tkMessageBox
        tkMessageBox.showinfo('Finished', message)
      else:
        print message
    elif action == 'saveback':
      for key, o in rom.model.items():
        output_filepath = os.path.join(output_folder, '%s.txt' % key)
        if not os.path.exists(output_filepath):
          continue
        if isinstance(o, chunks.PointerDataBlock) and o.DataType == chunks.TerminatedString:
          values = []
          f = codecs.open(output_filepath, 'r', 'utf-8')
          try:
            if f.read(1) != u'\uFEFF':
              f.seek(0)
            for l in f:
              if re.match('^\s*(#.*)?$', l):
                continue
              match = re.match(r'^\s*(\d+)\s*[\.:] ?(.*?)[\r\n]*$', l)
              if not match:
                raise Exception('invalid content in file: ' + l)
              index = int(match.group(1))
              value = match.group(2)
              if index == len(values):
                values.append(value)
              else:
                if index > len(values):
                  values.extend([None for x in range(len(values), index+1)])
                values[index] = value
          finally:
            f.close()
          try:
            o.write(rom, values)
          except:
            error_context = 'while importing "%s.txt"' % key
            raise
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
