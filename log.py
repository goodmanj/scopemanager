""" A text widget that can't be edited by the user."""

try:
    # for Python2
    from Tkinter import *
except ImportError:
    # for Python3
    from tkinter import *

class Log(Text):
    """A text widget that can't be edited by the user."""
    def __init__(self,master=None):
        Text.__init__(self,master)
        self.config(state=DISABLED)
    def insert(self, index, chars, *args):
        """Add text to the widget without letting the user type in it."""
        self.config(state=NORMAL)
        Text.insert(self,index, chars, args)
        self.config(state=DISABLED)        
    def delete(self, index1, index2=None):
        """Delete text from the widget without letting the user type in it."""
        self.config(state=NORMAL)
        Text.delete(self, index1, index2)
        self.config(state=DISABLED)
    def log(self, chars):
        """Add text to the end of the widget and make sure it's visible."""
        self.insert(END, chars+'\n')
        self.see(END)
        self.update()

