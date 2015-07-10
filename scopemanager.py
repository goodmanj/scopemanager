""" Telescope Manager

Issues useful commands to Celestron NexStar telescopes, and provides a Stellarium-compatible
network interface to allow it to issue slew commands and receive position updates.

This Python script relies on Tkinter to provide a GUI.  If it's not installed on
your system, you're in trouble.
"""

import scopemanagerui

gui = scopemanagerui.ScopeManagerUI()
gui.master.title("Telescope Manager")
gui.mainloop()
