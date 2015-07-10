""" RADec:  A class to store and convert right ascension/declination
coordinates """
import struct

class RADec(tuple):
    
    """Internal storage format for RADec object: two floating-point numbers:
    self[0]: decimal hours of right ascension
    self[1]: decimal degrees of declination"""

    def unsigned_to_signed_int(x):
        """Convert unsigned integers to Python signed integers using
        twos complement."""
        if x>0x7FFFFFFF:
            x=-int(0x100000000-x)
        return x
      
    def signed_to_unsigned_int(x):
        """Convert Python signed integers to unsigned integers using
        twos complement."""
        if x<0:
            x=int(0x100000000+x)
        return x

    def valid(self):
        """is RA between 0 and 24, and dec between -90 and 90?"""
        ra = self[0]
        dec = self[1]
        if (ra > 24 or ra < 0 or dec > 90 or dec < -90):
            return False
        else:
            return True

    def __new__(cls,*args, **kw):
        self = tuple.__new__(cls, *args, **kw)
#        if not self.valid():
#            raise ValueError("RA or dec out of bounds.")
        return self

    def fromStellarium(stellra,stelldec):
        """Create a RADec object from Stellarium's data format."""

        """Stellarium format: stellra is an unsigned integer,
        where 0h = 0x00000000, 24h = 0xFFFFFFFF.
        stelldec is a signed integer, where
        -90 = -0x40000000, +90 = 0x40000000"""
        ra_decimal_hours = (24*stellra / 0x100000000)
        declination_decimal_deg = (90*stelldec / 0x40000000)
        return RADec((ra_decimal_hours, declination_decimal_deg))

    def toStellarium(self):
        """Convert a RADec object to Stellarium's data format"""

        """See fromStellarium() for Stellarium data format."""
        stellra = int(0x100000000*self[0]/24)
        stelldec = int(0x40000000*self[1]/90)
        return (stellra,stelldec)
    
    def fromNexstar(response):
        """Create a RADec object from NexStar's data format."""

        """NexStar format: b'RRRRRRRR,DDDDDDDD', where RRRRRRRR is the ascii hexadecimal
        representation of an unsigned integer, the right ascension, where "00000000" = 0h
        and "FFFFFFFF" = 24h.  DDDDDDDD is the same for declination, but twos complemented
        for negative declination. "40000000" is +90 declination, "00000000" is zero, and
        "C0000000" is -90.
        """

        if not len(response)>15:
            raise ValueError("Invalid NexStar coordinate")
        rahrs = 24*int(response[0:8],16)/0x100000000
        decdeg = 360*RADec.unsigned_to_signed_int(int(response[9:17],16))/0x100000000
        return RADec((rahrs,decdeg))

    def toNexstar(self):
        """Convert a RADec object to NexStar's data format."""
        intra = int(0x100000000*self[0]/24)
        intdec = RADec.signed_to_unsigned_int(int(0x100000000*self[1]/360))
        msg = '%08X,%08X' % (intra,intdec)
        return bytes(msg,'ascii')

    def fromMeade(raresp,decresp):
        """Create a RADec object from Meade's data format."""

        """Meade format: decresp = b'sDD*MM'SS#, raresp = b'HH:MM:SS#' where s is sign,
        HH,DD,MM,SS are hours, degrees, minutes, seconds.
        """

        if len(raresp)< 9:
            rahrs=0
            raise ValueError("Invalid Meade right ascension.")
        rahrs = int(raresp[0:2]) + int(raresp[3:5])/60 + int(raresp[6:8])/3600
        if len(decresp) < 10:
            decdeg=0
            raise ValueError("Invalid Meade declination.")
        if decresp[0:1] == b'+':   # Positive declination
            decdeg = int(decresp[1:3]) + int(decresp[4:6])/60 + int(decresp[7:9])/3600
        else:                     # Negative
            decdeg = -int(decresp[1:3]) - int(decresp[4:6])/60 - int(decresp[7:9])/3600
        return RADec((rahrs,decdeg))

    def toMeade(self):
        """Convert a RADec object to Meade's data format."""
        msgra = '%02d:%02d:%02d#' % self.ra_hms();
        msgdec = '%+03d*%02d\'%02d#' % self.dec_dms();
        return (bytes(msgra,'ascii'), bytes(msgdec,'ascii'))
    
    def ra(self):
        """Right ascension in decimal degrees."""
        return self[0]
    def dec(self):
        """Declination in decimal degrees."""
        return self[1]
    
    def ra_hms(self):
        """Right ascension as an [hour, minute, second] list."""
        rahours = int(self[0])
        ra_decimal_mins = ((self[0] - rahours)*60)
        ramin = int(ra_decimal_mins)
        rasec = (ra_decimal_mins-ramin)*60
        return (rahours, ramin,rasec)
    
    def dec_dms(self):
        """Declination as a [degree, minute, second] list.  For negative declinations, the sign
        is carried only in the degrees."""
        decldeg = int(self[1])
        declination_decimal_mins = abs((self[1] - decldeg)*60)  # Convert to positive minutes and seconds
        declmin = int(declination_decimal_mins)
        declsec = (declination_decimal_mins-declmin)*60
        return (decldeg, declmin, declsec)

    def rastr(self):
        """Right ascension as a formatted string."""
        return "%dh%dm%ds" % self.ra_hms() 

    def decstr(self):
        """Declination as a formatted string."""
        return "%dd%dm%ds" % self.dec_dms() 
