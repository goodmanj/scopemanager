"""Communicates with a NexStar-compatible telescope through a serial port.
Serial port must be passed in at instance creation."""

import serial
import radec
import time

class NexStar:

    def unsigned_to_signed_int(x):
        if x>0x7FFFFFFF:
            x=-int(0x100000000-x)
            return x    
    
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
                print('NexStar telescope is not responding.')
                self.ready = False
                return
            else:
                self.ready = True
            self.ser.flush()
    
    def close(self):
        try:
            self.ser.close()
        except:
            pass
        self.ready = False

    def istracking(self):
        """ True if scope is tracking the sky to compensate for Earth's
        rotation."""
        self.ser.flushInput()
        self.ser.write(b't')
        response = self.ser.read(2)
	    
        if (len(response) < 2):
            print('No response from telescope.  Check communications.')
        elif response[0] == 0:
            return False
        elif response[0] > 0:
            return True
        else:
            print('Unexpected response from telescope:')
            response
            return None

    def settracking(self,dotrack):
        """ Set dotrack=True to start tracking the sky to
        compensate for Earth's rotation; dotrack=False to stop.  If you're
        in the southern hemisphere, hack this script."""
        self.ser.flushInput()
        if dotrack:
            self.ser.write(b'T\x02')
#            self.ser.write(b'T\x01')   # for southern hemisphere
        else:
            self.ser.write(b'T\x00')
        response = self.ser.read(1)
        response
        newtrack = self.istracking()
        if (newtrack == dotrack):
            return newtrack
        else:
            print('Tracking not successfully changed to',dotrack)
            return newtrack

    def getposition(self,dump=False):
        """Request current telescope position.  Result is returned as a
        RADec object (see radec.py)"""
        self.ser.flushInput()
        self.ser.write(b'e')
        response = self.ser.read(18)
        if dump:
            print(response)
        if (len(response)<18):
            print('Unexpected response from telescope:')
            response
            return None
        return radec.RADec.fromNexstar(response)

    def getaltaz(self,dump=False):
        """Request current telescope alt/az position.  Result is returned as a
        RADec object (see radec.py)"""
        self.ser.flushInput()
        self.ser.write(b'z')
        response = self.ser.read(18)
        if dump:
            print(response)
        if (len(response)<18):
            print('Unexpected response from telescope:')
            response
            return None
        return radec.RADec.fromNexstar(response)

    def stop(self):
        """Stop all telescope motion by setting motor speed to zero."""
        self.sleweast(0)
        return self.slewnorth(0)
    
    def sleweast(self,speed):
        """Slew telescope east.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        speed = min(max(int(speed),0),9)            
        cmd = b'P'+bytes([2,16,37,speed,0,0,0])
        self.ser.flushInput()
        self.ser.write(cmd)
        self.listenforconfirm()

    def slewwest(self,speed):
        """Slew telescope west.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        speed = min(max(int(speed),0),9)            
        cmd = b'P'+bytes([2,16,36,speed,0,0,0])
        self.ser.flushInput()
        self.ser.write(cmd)
        self.listenforconfirm()

    def slewnorth(self,speed):
        """Slew telescope north.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!
        Note: slewnorth() goes north if telescope is pointed east; goes south
        if telescope is pointed west.  Don't blame me, blame Celestron."""
        speed = min(max(int(speed),0),9)            
        cmd = b'P'+bytes([2,17,36,speed,0,0,0])
        self.ser.flushInput()
        self.ser.write(cmd)
        self.listenforconfirm()
    
    def slewsouth(self,speed):
        """Slew telescope south.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!
        Note: slewsouth() goes south if telescope is pointed east; goes north
        if telescope is pointed west.  Don't blame me, blame Celestron."""
        speed = min(max(int(speed),0),9)            
        cmd = b'P'+bytes([2,17,37,speed,0,0,0])
        self.ser.flushInput()
        self.ser.write(cmd)
        self.listenforconfirm()

    def goto(self,pos):
        """Command telescope to GOTO position pos.
        pos must be a RADec object (see radec.py)"""
        print('Moving scope to ',pos.ra(),pos.dec())
        nspos = pos.toNexstar()
        cmd = b'r'+nspos
        print(cmd)
        self.ser.flushInput()       
        self.ser.write(cmd)
        self.listenforconfirm()

    def sync(self,pos):
        """Command telescope to SYNC on position pos.
        pos must be a RADec object (see radec.py)"""
        print('Syncing scope to ',pos.ra(),pos.dec())
        nspos = pos.toNexstar()
        cmd = b's'+nspos
        print(cmd)
        self.ser.flushInput()       
        self.ser.write(cmd)
        self.listenforconfirm()

    def undosync(self):
        """Command telescope to clear SYNC"""
        print('Clearing SYNC')
        cmd = b'u'
        print(cmd)
        self.ser.flushInput()       
        self.ser.write(cmd)
        self.listenforconfirm()

    def listenforconfirm(self,numbytes=1):
        """Listen for confirmation from telescope.  No detailed parsing:
        just listens for any reply of length numbytes."""
        response = self.ser.read(numbytes)
        if (len(response)<numbytes):
            print('Unexpected response from telescope:')
            response

    def write(self,data):
        """Send arbitrary data to the telescope."""
        self.ser.write(data)
    def read(self,bytecount):
        """read arbitrary data from the telescope."""
        return self.ser.read(bytecount)

    def getrate(self):
        """Scope motion rate, in arcseconds/second"""
        startpos = self.getposition()
        time.sleep(5)
        endpos = self.getposition()
        return ((endpos[0]-startpos[0])*3600/5,(endpos[1]-startpos[1])*3600/5)
    
    def getaltazrate(self):
        """Scope motion rate, in arcseconds/second"""
        startpos = self.getaltaz()
        time.sleep(5)
        endpos = self.getaltaz()
        return ((endpos[0]-startpos[0])*3600/5,(endpos[1]-startpos[1])*3600/5)