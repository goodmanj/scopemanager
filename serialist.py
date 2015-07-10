""" A list of available serial ports on this machine.  Does file-hunting in /dev
on Mac/Linux; does registry hacking on Windows.  Call the update method to refresh
the list."""

import platform
import itertools

if (platform.system() == 'Windows'):
    import winreg
else:
    import glob
        
class Serialist(list):
    def __init__(self):
        list.__init__(self)
        self.update()
    
    def update(self):
        """Update the list of active serial ports."""
        list.__init__(self)
        plat = platform.system()
        if (plat == 'Windows'):
            """Totally stolen from http://stackoverflow.com/questions/1205383/"""
            path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            except:
                raise EnvironmentError
            
            for i in itertools.count():
                try:
                    val = winreg.EnumValue(key, i)
                    self.append(str(val[1]))
                except:
                    break
        elif (plat == 'Darwin'):
            """Mac has lots of useless /dev/tty*'s, but the /dev/cu*'s seem to
            represent real devices.  And most of the time you want a callout
            device anyway."""
            print(glob.glob('/dev/cu.*'))
            list.__init__(self,glob.glob('/dev/cu.*'))
                    
        """Only Windows and Mac for now.  Linux should be the same as Mac,
        but I haven't tested it yet."""
