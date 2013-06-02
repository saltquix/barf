
import os, sys, ConfigParser, codecs
from contextlib import contextmanager
import Tkinter, tkFileDialog, tkMessageBox, tkSimpleDialog
from RiverCityRansomRom import RiverCityRansomRom

def setTkIcon(root):
  this_dir, this_filename = os.path.split(__file__)
  img = Tkinter.PhotoImage(file=os.path.join(this_dir, "data", "alex.gif"))
  root.tk.call('wm', 'iconphoto', root._w, img)

class Cancellation(Exception):
  pass

class Hackery(object):
  def __init__(self, **kwargs):
    self.filenames = kwargs
    self.root = Tkinter.Tk()
    self.root.withdraw()
    setTkIcon(self.root)
    with self.config(read_only=True) as cfg:
      if cfg.has_option('Paths', 'ROMs'):
        self.rom_folder = cfg.get('Paths', 'ROMs')
      else:
        self.rom_folder = os.path.split(__file__)[0]
    self.phase_stack = ['']
    self.rom_path = None

  @contextmanager
  def phase(self, name):
    self.phase_stack.append(name)
    try:
      yield
      self.phase_stack.pop()
    finally:
      pass

  @contextmanager
  def config(self, read_only=False):
    cfg = ConfigParser.ConfigParser()
    cfg.read('barf.cfg')
    yield cfg
    if not read_only:
      with open('barf.cfg', 'wb') as cfgfile:
        cfg.write(cfgfile)

  def get_phase(self):
    return self.phase_stack[-1]

  def __enter__(self):
    if not self.rom_path and len(sys.argv) > 1:
      self.rom_path = sys.argv[1]
    if not self.rom_path:
      self.rom_path = tkFileDialog.askopenfilename(
        title = 'Please choose a River City Ransom ROM image file',
        filetypes = [('NES ROMs', '*.nes'), ('All files', '*.*')],
        initialdir = self.rom_folder)
      if not self.rom_path:
        raise Cancellation()
      with self.config() as cfg:
        if not cfg.has_section('Paths'):
          cfg.add_section('Paths')
        cfg.set('Paths', 'ROMs', os.path.split(self.rom_path)[0])
    self.rom = RiverCityRansomRom()
    self.rom.load(self.rom_path)

    if len(sys.argv) > 2:
      self.output_folder = sys.argv[2]
    else:
      if cfg.has_option('Paths', 'Output'):
        self.output_folder = cfg.get('Paths', 'Output')
      else:
        self.output_folder = 'output'
      self.output_folder = tkFileDialog.askdirectory(
        title = 'Please choose a data directory',
        initialdir = self.output_folder,
        mustexist = True)
      if not self.output_folder:
        raise Cancellation()
      with self.config() as cfg:
        if not cfg.has_section('Paths'):
          cfg.add_section('Paths')
        cfg.set('Paths', 'Output', self.output_folder)
    if not os.path.exists(self.output_folder):
      os.makedirs(self.output_folder)
    self.action = 'extract'
    if any(os.path.exists(os.path.join(self.output_folder, self.filenames[fn])) for fn in self.filenames):
      action = tkMessageBox.askquestion(
        'Save back changes?',
        'There are data files in this folder. Do you want to save data from these files back onto the ROM?\n\n'
        + 'Click "Yes" to save changed data files back to the ROM.\n'
        + 'Click "No" to export again, writing over existing data files.\n'
        + 'Click "Cancel" to do nothing.',
        type = tkMessageBox.YESNOCANCEL)
      if action == 'yes':
        self.action = 'saveback'
      elif action != 'no':
        raise Cancellation()
    return self
  def opentxt(self, fn, mode):
    f = codecs.open(os.path.join(self.output_folder, self.filenames[fn]), mode, 'utf-8')
    if 'r' in mode and f.read(1) != u'\uFEFF':
      f.seek(0)
    elif 'w' in mode:
      # add BOM. screw the whiners
      f.write(u'\uFEFF')
    return f
  def finishsaveback(self):
    if self.rom.clean:
      self.rom.title = tkSimpleDialog.askstring( \
        'Please enter a title', \
        'Please enter a title for the hack:', \
        initialvalue='Untitled '+self.rom.title+' Hack')
    self.rom.save(self.rom_path)
    tkMessageBox.showinfo('Finished', 'Finished data import from ' + self.output_folder + '\ninto ' + self.rom_path)
  def finishexport(self):
    tkMessageBox.showinfo('Finished', 'Finished data export to ' + self.output_folder)
  def __exit__(self, type, e, traceback):
    if e:
      phase = self.get_phase()
      tkMessageBox.showerror('Error %s' % phase, 'Oops! An error occurred %s:\n\n%s' % (phase or '', unicode(e)))
