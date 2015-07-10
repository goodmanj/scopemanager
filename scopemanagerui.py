""" ScopeManagerUI

Tkinter user interface for Scope Manager.

"""
import stellariumserver
import meade
import nexstar
import radec
import time
import serialist
import log
import inspect

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


class MeadePanel(Frame):
    # Meade-specific commands
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.starlock = IntVar()
        self.starlockCheckbox = Checkbutton (self, text='Starlock', variable = self.starlock, \
                                          command = self.togglestarlock)
        self.starlockCheckbox.pack(anchor=E)
        self.safemode = IntVar()
        Radiobutton(self, text="Safe Mode", variable=self.safemode, value=1, command=self.togglesafemode).pack(anchor=W)
        Radiobutton(self, text="Scope Active", variable=self.safemode, value=2, command=self.togglesafemode).pack(anchor=W)
    
    def togglesafemode(self):
        return
    
    def togglestarlock(self):
        return

class NexStarPanel(Frame):
    # NexStar-specific commands
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.safemode = IntVar()
        Radiobutton(self, text="Safe Mode", variable=self.safemode, value=1, command=self.togglesafemode).pack(anchor=W)
        Radiobutton(self, text="Scope Active", variable=self.safemode, value=2, command=self.togglesafemode).pack(anchor=W)

    def togglesafemode(self):
        return
    
# The main window
class ScopeManagerUI(Frame):
    def __init__(self, master=None):
        """Create UI, create scope and stellarium
        communication objects, and start polling."""
        Frame.__init__(self,master)
        self.grid()
        self.scope = None
        self.createWidgets()
        self.stellarium = stellariumserver.StellariumServer()
        self.poll()
        self.sync_confirm = time.clock()
        self.master.protocol("WM_DELETE_WINDOW", self.quit)
        
    
    def poll(self):
        """Handle TCP and serial comms periodically"""
        """Call this poller again in 1 second."""
        self.after(1000, self.poll)

        """Listen for commands from Stellarium, send them on to scope."""        
        gotopos,syncpos = self.stellarium.receive()
        if gotopos is not None:
            self.messages.log('Stellarium commands GOTO '+str(gotopos.ra())+' '+str(gotopos.dec()))
            if self.scope is not None and self.scope.ready:
                self.scope.goto(gotopos)

        if syncpos is not None:
            self.messages.log('Stellarium commands SYNC '+str(syncpos.ra())+' '+str(syncpos.dec()))
            if self.scope is not None and self.scope.ready:
                if syncpos.dec() < 0:
                    self.messages.log("Can't sync to southern hemisphere.  Blame Celestron.")
                else:
                    if (time.clock() - self.sync_confirm > 10):
                        self.messages.log("Confirm SYNC: make sure telescope is centered on Stellarium's target, and SYNC again.")
                        self.sync_confirm = time.clock()
                    else:
                        self.scope.sync(syncpos)
                        self.stellarium.send(syncpos,type='SYNC')
                        self.sync_confirm = time.clock() - 20

        """Get scope's current position, and report it to Stellarium and in this window."""        
        if self.scope is not None and self.scope.ready:
            scopepos = self.scope.getposition(dump=True)
            if scopepos is not None:
                self.stellarium.send(scopepos)
                self.positiontext.set("RA: %s\nDec: %s" % (scopepos.rastr(),scopepos.decstr()))
    
    def quit(self):
        if self.scope is not None and self.scope.ready:
            self.scope.settracking(False)
            if (self.scope.istracking()):
                self.messages.log('WARNING: Tracking is still on!')
                time.sleep(3)
            self.scope.close()
        Frame.quit(self)
    
    def createWidgets(self):
        
        self.speedLabel = Label(self, text='Slew Speed:')
        self.speedSlider = Scale (self, from_=9, to = 1, orient="vertical")
        
        """Direction arrows send slew commands when pressed, and stop commands when released."""
        self.northButton = Button (self, text='^')
        self.northButton.bind("<Button-1>", self.north)
        self.northButton.bind("<ButtonRelease-1>", self.stop)
        self.southButton = Button (self, text='v')
        self.southButton.bind("<Button-1>", self.south)
        self.southButton.bind("<ButtonRelease-1>", self.stop)
        self.eastButton  = Button (self, text='<')
        self.eastButton.bind("<Button-1>", self.east)
        self.eastButton.bind("<ButtonRelease-1>", self.stop)
        self.westButton  = Button (self, text='>')
        self.westButton.bind("<Button-1>", self.west)
        self.westButton.bind("<ButtonRelease-1>", self.stop)
        self.stopButton  = Button (self, text='stop',command = self.stop)

        self.fliplabel = Label (self, text='Pier Flip:')
        flipList = ['East','West']
        self.flip = StringVar()
        self.flip.set(flipList[0])
        self.flipmenu = OptionMenu (self, self.flip, *flipList)
        self.flipmenu.config(width=7)
        
        self.tracking = IntVar()
        self.trackCheckbox = Checkbutton (self, text='Tracking', variable = self.tracking, \
                                          command = self.toggletrack)
                
        self.positiontext = StringVar()
        self.positiontext.set('Not Connected')
        self.positionlabel = Label (self, textvariable=self.positiontext,height=2,width=15)

        self.undosyncButton = Button (self, text='Undo Sync', command = self.undosync )
        self.quitButton = Button (self, text='Quit', command = self.quit )

        self.messages = Log(self)
        self.messages.config(width=30,height=8)

        self.portLabel = Label(self, text='Serial Port:')
        
        # Grid 'em all up
        self.speedLabel.grid(column=1,row=1)
        self.speedSlider.grid(column=1,row=2,rowspan=3)
        
        self.northButton.grid(column=3,row=2)
        self.southButton.grid(column=3,row=4)
        self.eastButton.grid(column=2,row=3)
        self.westButton.grid(column=4,row=3)        
        self.stopButton.grid(column=3,row=3)        
        
        
        self.portLabel.grid(column=1,row=0)
        self.trackCheckbox.grid(column=0,row=5,columnspan=2)

        self.fliplabel.grid(column=5,row=1)
        self.flipmenu.grid(column=5,row=2)
        
        self.positionlabel.grid(column=2,row=5,columnspan=3)
        self.undosyncButton.grid(column=5,row=4)
        self.quitButton.grid(column=5,row=5)
        
        self.messages.grid(column=1,row=7,columnspan=5)

        """serialist.Serialist() returns a list of active serial ports on this machine.
        This list is not updated while Scope Manager is running."""
        portList = serialist.Serialist()
        self.scopePorts = [];        
        self.scopeTypes = [];
        self.port = StringVar()
        self.scopespecific = None;
        for port in portList:
            self.update()
            self.messages.log('Scanning '+port+' for NexStar telescopes.')
            scope = nexstar.NexStar(port)
            if scope.ready:
                self.messages.log('Found NexStar telescope on port '+port+'.')
                self.scopePorts.append(port)
                self.scopeTypes.append('NexStar')
            else:
                scope.close()
                del scope
                self.update()
                self.messages.log('Scanning '+port+' for Meade telescopes.')
                scope = meade.Meade(port)
                if scope.ready:
                    self.messages.log('Found Meade telescope on port '+port+'.')
                    self.scopePorts.append(port)
                    self.scopeTypes.append('Meade')
            scope.close()
            del scope
            
        if not self.scopePorts:
            self.messages.log('No serial ports found.  Connect a serial device and restart Telescope Manager.\n')
            portList = ['NONE FOUND']
        else:
            self.port.set(self.scopePorts[0])
            self.updateport()
        self.portmenu = OptionMenu (self, self.port, *(self.scopePorts), command=self.updateport)
        self.portmenu.grid(column=2,row=0,columnspan=4)

        self.messages.insert(END,'Telescope Manager ready.\n')

    def undosync(self):
        self.scope.undosync()
    
    def north(self, event=None):
        """Command scope to slew north.  Annoyingly, when the scope is pointed west
        the north/south directions are backward, so use the "Pier Flip" setting to
        reverse directions."""
        if self.scope is not None and self.scope.ready:
            if (self.flip.get() == 'East'):
                self.scope.slewnorth(self.speedSlider.get())
            else:
                self.scope.slewsouth(self.speedSlider.get())
            self.messages.log('Slewing north at speed '+str(self.speedSlider.get()))
        else:
            self.messages.log('Not connected to a telescope.')

    def south(self, event=None):
        """Command scope to slew north.  Annoyingly, when the scope is pointed west
        the north/south directions are backward, so use the "Pier Flip" setting to
        reverse directions."""
        if self.scope is not None and self.scope.ready:
            if (self.flip.get() == 'East'):
                self.scope.slewsouth(self.speedSlider.get())
            else:
                self.scope.slewnorth(self.speedSlider.get())
            self.messages.log('Slewing south at speed '+str(self.speedSlider.get()))
        else:
            self.messages.log('Not connected to a telescope.')

    def east(self, event=None):
        """Command scope to slew east."""
        if self.scope is not None and self.scope.ready:
            self.scope.sleweast(self.speedSlider.get())
            self.messages.log('Slewing east at speed '+str(self.speedSlider.get()))
        else:
            self.messages.log('Not connected to a telescope.')

    def west(self, event=None):
        """Command scope to slew east."""
        if self.scope is not None and self.scope.ready:
            self.scope.slewwest(self.speedSlider.get())
            self.messages.log('Slewing west at speed '+str(self.speedSlider.get()))
        else:
            self.messages.log('Not connected to a telescope.')

    def stop(self, event=None):
        """Command scope to slew east."""
        if self.scope is not None and self.scope.ready:
            self.scope.stop()     
            self.messages.log('Stopped')
        else:
            self.messages.log('Not connected to a telescope.')
            
    def updateport(self,event=None):
        """Handle a change in the active serial port.  Close the current port
        if it's open and attempt to open the new one."""
        if self.scope is not None and self.scope.ready:
            if self.scopespecific is not None:
                self.scopespecific.grid_remove()                
            if (self.scope.istracking()):
                self.messages.log('WARNING: Tracking is still on!')
                time.sleep(3)
            self.scope.close()
        newscopetype = self.scopeTypes[self.scopePorts.index(self.port.get())]
        self.messages.log('Looking for '+newscopetype+' on '+str(self.port.get())+'...')       
        if newscopetype=='NexStar':
            self.scope = nexstar.NexStar(str(self.port.get()))
            self.scopespecific = NexStarPanel(self)
        else:
            self.scope = meade.Meade(str(self.port.get()))
            self.scopespecific = MeadePanel(self)
        if self.scope is not None and self.scope.ready:
            self.messages.log('Connected to '+newscopetype+' on '+str(self.port.get()))
            self.tracking.set(int(self.scope.istracking()))
            self.scopespecific.grid(column=1,row=6,columnspan=5)
        else:
            self.scope.close()
            self.messages.log("Can't connect to scope on "+str(self.port.get()))
            self.positiontext.set('Not Connected')

    def toggletrack(self,event=None):
        """Handle a change in the state of the "Tracking" checkbox."""
        if self.scope is not None and self.scope.ready:
            newtrack = self.scope.settracking(bool(self.tracking.get()))
            self.tracking.set(int(newtrack))
            self.messages.log('Tracking changed to '+str(bool(self.tracking.get())))
        else:
            self.messages.log('Not connected to a telescope.')
    
