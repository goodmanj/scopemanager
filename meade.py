"""Communicates with a Meade-compatible telescope through a serial port.
Serial port must be passed in at instance creation."""

import serial
import radec
import time

class Meade:

    def __init__(self,comport=None):
        self.ready = False
        if comport is not None:
            self.open(comport)

    def ready(self):
        """True if connection to a Meade-compatible scope is established.
        Updated only during open() and close(), so if the scope gets hit by
        lightning, ready() may still return True."""
        return self.ready
    
    def open(self,comport):
        """Open a serial connection on port comport.  Sends "wake" and "align status"
        commands to the scope, enters high precision coordinate mode."""
        self.ready = False
        try:
            self.ser = serial.Serial(comport,9600,timeout=5)
            self.ready = True
        except:
            print('Failed to open serial port ',comport)     
            self.ready = False
        if self.ready:
            # Send some greetings to the scope to wake it up
            self.ser.flushInput()
            self.ser.write(b':hW#')       # Wake up!
            self.ser.write(b':GW#')       # Query alignment status
            self.ser.flushInput()
            self.ser.write(b':GW#')       # Query alignment status
            resp = self.ser.read(4)
            if len(resp) < 4:
                print('Meade telescope is not responding.')
                self.ready = False
            else:
                print('Meade telescope responded.')
                self.ready = True
                if resp[2:3] == b'0':
                    print('Warning: Telescope is not aligned.')
            self.ser.flush()
            self.ser.write(b':GD#')     # Get declination
            resp = self.ser.read(10)
            if len(resp) < 10:           # short declination returned
                self.ser.write(b':U#')   # toggle precision
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
        self.ser.write(b':GW#')
        response = self.ser.read(4)
	    
        if (len(response) < 4):
            print('No response from telescope.  Check communications.')
        elif response[1:2] ==b'N':
            return False
        elif response[1:2] ==b'T':
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
            self.ser.write(b'TQ#')
        else:
            self.ser.write(b':ST00.0#')
        response = self.ser.read(1)
        response
        newtrack = self.istracking()
        if (newtrack == dotrack):
            return newtrack
        else:
            print('Tracking not successfully changed to',dotrack)
            return newtrack
        
    def setstarlock(self,dostarlock):
        """ Set dostarlock=true to engage Starlock autoguiding."""
        self.ser.flushInput()
        if dostarlock:
            self.ser.write(b':MgS1#')
        else:
            self.ser.write(b':MgS0#')

    def getposition(self,dump=False):
        """Request current telescope position.  Result is returned as a
        RADec object (see radec.py)"""
        self.ser.flushInput()
        self.ser.write(b':GD#')         # get declination
        decresp = self.ser.read(10)
        self.ser.write(b':GR#')         # get right ascension
        raresp = self.ser.read(9)
        if dump:
            print('RA: ',raresp,' Dec: ',decresp)
        try:
            pos = radec.RADec.fromMeade(raresp,decresp)
        except ValueError:
            pass
        return radec.RADec.fromMeade(raresp,decresp)

    def getaltaz(self,dump=False):
        """Request current telescope alt/az position.  Result is returned as a
        RADec object (see radec.py)"""
        self.ser.flushInput()
        self.ser.write(b':GZ#')         # get azimuth
        azmresp = self.ser.read(10)
        self.ser.write(b':GR#')         # get altitude
        altresp = self.ser.read(9)
        if dump:
            print('Az: ',azmresp,' Alt: ',altresp)
        return radec.RADec.fromMeade(azmresp,altresp)

    def stop(self):
        """Stop all telescope motion."""
        self.ser.flushInput()
        self.ser.write(b':Q#')

    def setrate(self,speed):
        """ Set slewing rate.  For Meade, there are four default rates, but for compatibility 
        we allow speeds from 0 to 9."""
        rate = int(((speed+1)*4)/10)
        rate = min(max(rate,0),3)         # Speed limit
        if (rate == 0):
            self.ser.write(b':RG#')
        elif (rate == 1):
            self.ser.write(b':RC#')
        elif (rate == 2):
            self.ser.write(b':RM#')
        elif (rate == 3):
            self.ser.write(b':RS#')
    
    def sleweast(self,speed):
        """Slew telescope east.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        self.setrate(speed)
        self.ser.write(b':Me#')

    def slewwest(self,speed):
        """Slew telescope west.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        self.setrate(speed)
        self.ser.write(b':Mw#')

    def slewnorth(self,speed):
        """Slew telescope north.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        self.setrate(speed)
        self.ser.write(b':Mn#')

    def slewsouth(self,speed):
        """Slew telescope south.  Speed should be between 0 (stopped) and 9
        (maximum slew rate).  Motion will continue until stop() is called!"""
        self.setrate(speed)
        self.ser.write(b':Ms#')

    def settarget(self,pos):
        """Set target position for goto or sync"""
        print('Setting target position to',pos.ra(),pos.dec())
        (meadera,meadedec) = pos.toMeade()
        self.ser.write(b':Sr'+meadera)
        resp = self.ser.read(1)
        if not int(resp):
            raise ValueError('Right ascension not accepted by telescope.')
        self.ser.write(b':Sd'+meadedec)
        resp = self.ser.read(1)
        if not int(resp):
            raise ValueError('Declination not accepted by telescope.')


    def goto(self,pos):
        """Command telescope to GOTO position pos.
        pos must be a RADec object (see radec.py)"""
        self.settarget(pos)
        print('Moving scope to ',pos.ra(),pos.dec())
        self.ser.write(b':MS#')
        resp = self.ser.read(1)
        if int(resp) > 0:
            print('Object below horizon limits.')

    def sync(self,pos):
        """Command telescope to SYNC on position pos.
        pos must be a RADec object (see radec.py)"""
        """Disabled for Meade: no way to clear."""
        print("Can't sync Meade.")
        """
        settarget(pos)
        print('Syncing scope to ',pos.ra(),pos.dec())
        self.ser.write(b':CM#')
        resp = self.ser.read(1)
        if len(resp) < 1:
            print('No response to sync command.')
        """

    def undosync(self):
        """Command telescope to clear SYNC"""
        """Disabled for Meade."""
        print("Can't sync Meade.")
        
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
