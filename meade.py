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
            self.ser = serial.Serial(comport,9600,timeout=2)
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
            print(resp)
            if len(resp) < 3:
                print('Meade telescope is not responding.')
                self.ready = False
                return
            else:
                print('Meade telescope responded.')
                self.ready = True
                self.ser.flushInput()
                self.ser.write(b':GD#')     # Get declination
                resp = self.ser.read(10)
                if len(resp) < 10:           # short declination returned
                    self.ser.write(b':U#')   # toggle precision
                self.ser.flushInput()
    
    def close(self):
        try:
            self.ser.close()
        except:
            pass
        self.ready = False

    def is_safe(self):
        """ True if scope motors are disabled, tracking off."""
        self.ser.flushInput()
        self.ser.write(b':GW#')
        response = self.ser.read(4)
	    
        if (len(response) < 4):
            print('No response from telescope.  Check communications.')
        elif response[1:2] ==b'N':
            return True
        elif response[1:2] ==b'T':
            return False
        else:
            print('Unexpected response from telescope:')
            response
            return False

    def set_safe(self,safe):
        """ Set safe=True to put telescope into sleep mode (motors and displays
        powered off); safe=False to put the telescope into active tracking mode.
        Kludge for safe=True: to start up tracking motors, telescope does a GOTO
        to its current position."""
        self.ser.flushInput()
        if not safe:
            self.ser.write(b':hW#') # Wake scope
            print('Waking scope')
            time.sleep(1)
            if self.is_safe(): # scope is not tracking
                pos = self.getposition()
                self.goto(pos)
                print('GOTO to enable tracking.')
        else: # Sleep scope
            self.ser.write(b':hN#')
            print('Putting scope to sleep.')
        
    def setstarlock(self,dostarlock):
        """ Set dostarlock=true to engage Starlock autoguiding."""
        self.ser.flushInput()
        if dostarlock:
            self.ser.write(b':MgS1#')
        else:
            self.ser.write(b':MgS0#')

    def sethighprecision(self,dohighprecision):
        """ Set dohighprecision=true to turn on high precision pointing."""
        self.ser.flushInput()
        self.ser.write(b':P#')  # Toggle high precision, can't be sure which way.
        resp = self.ser.read(14)
        if (len(resp)> 1):
            if (dohighprecision and (resp[0] == 'L')) or (not dohighprecision and (resp[0] == 'H')):  # Wrong precision
                self.ser.write(b':P#') # Retoggle.
        else:
            print('No response from scope')

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
        if len(resp) > 0:            
            if int(resp) > 0:
                print('Object below horizon limits.')
        else:
            print('No response from scope.')
            
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

    def focus(self,time):
        time = min(max(time,-65000),65000)  # Limit 65000 ms focus
        focusmsg = (':FP%+d#'%time).encode()
        self.ser.flush()
        print(focusmsg)
        self.ser.write(focusmsg)

    def focushalt(self):
        self.ser.flush()
        self.ser.write(b':FQ#')
        
    def focusspeed(self,speed):
        speed = min(max(speed,1),4)
        self.ser.flush()
        self.ser.write((':F%1d#'%speed).encode())
