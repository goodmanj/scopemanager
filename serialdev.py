""" Generic methods class for serial I/O."""

class serialdev:
    
    def __init__(self,comport=None):
        self.ready = False
        if comport is not None:
            self.open(comport)

    def ready(self):
        """True if connection to a NexStar-compatible scope is established.
        Updated only during open() and close(), so if the scope gets hit by
        lightning, ready() may still return True."""
        return self.ready
    
    def open(self,comport):
        """Open a serial connection on port comport.  Sends "are you
        there" messages to verify connection to a NexStar-compatible scope."""
        self.ready = False
        try:
            self.ser = serial.Serial(comport,9600,timeout=1)
            self.ready = True
        except:
            print('Failed to open serial port ',comport)     
            self.ready = False
        if self.ready:
            # Send some greetings to the scope to wake it up
            self.ser.write(b'V')       # Scope version
            resp = self.ser.read(3)
            self.ser.write(b'V')
            resp = self.ser.read(3)
            self.ser.write(b'Kq')      # Ask scope to echo "q"
            resp = self.ser.read(2)
            if not(resp == b'q#'):
                print('Telescope is not responding.')
                self.ready = False
            else:
                self.ready = True
            self.ser.flush()
    
    def close(self):
        if self.ready:
            self.ser.close()
            self.ready = False
