
import os

def setTkIcon(root):
  import Tkinter
  this_dir, this_filename = os.path.split(__file__)
  img = Tkinter.PhotoImage(file=os.path.join(this_dir, "data", "alex.gif"))
  root.tk.call('wm', 'iconphoto', root._w, img)
