import struct
import socket
import select
import time

import radec
     
class StellariumServer:
     """ TCP/IP interface to send and receive information from Stellarium, a
     planetarium program http://www.stellarium.org/"""

     def __init__(self):
          """Open two TCP/IP sockets, one for GOTO commands from Stellarium
          (port 10001), one for SYNC commands (port 10002)"""

          TCP_IP = '127.0.0.1'
          GOTO_PORT = 10001
          SYNC_PORT = 10002
          BUFFER_SIZE = 1024
     
          self.gotoport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          self.gotoport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          self.gotoport.bind((TCP_IP, GOTO_PORT))
          self.gotoport.setblocking(0)
          self.gotoport.listen(1)
     
          self.syncport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          self.syncport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          self.syncport.bind((TCP_IP, SYNC_PORT))
          self.syncport.setblocking(0)
          self.syncport.listen(1)
     
          self.socklist = [self.gotoport,self.syncport]
          self.gotoportlist = []
          self.syncportlist = []

     def receive(self):
          """Listen for incoming connections and data sent from Stellarium.
          Non-blocking I/O."""
          syncpos = None
          gotopos = None
          """Dude I totally learned how select() works!"""
          ready_to_read, ready_to_write, in_error = select.select(self.socklist,self.socklist,self.socklist,0)  # Non-blocking read
          if (ready_to_read):  # Some sockets want attention
               for sok in ready_to_read:
                    if (sok is self.gotoport):   #Master goto port connection
                         conn, addr = sok.accept()
                         print('Connection address:', addr)
                         self.socklist.append(conn)
                         self.gotoportlist.append(conn)
                    elif (sok is self.syncport):  #Master sync port connection
                         conn, addr = sok.accept()
                         print('Connection address:', addr)
                         self.socklist.append(conn)
                         self.syncportlist.append(conn)
                    else:  # it's an accepted connection
                         data = sok.recv(2)
                         if not data: 
                              print('closing connection')
                              self.socklist.remove(sok)                    
                              if sok in self.gotoportlist:
                                   self.gotoportlist.remove(sok)
                              if sok in self.syncportlist:
                                   self.syncportlist.remove(sok)                                   
                              sok.close()
                         else:
                              """Stellarium data format:
                              2 bytes (length of message)
                              2 bytes (short int, message type)
                              8 bytes (long long int, microseconds since epoch)
                              4 bytes (unsigned int, right ascension)
                              4 bytes (signed int, declination)"""
                              
                              leng = struct.unpack('<H',data)[0]
                              if (leng == 20):
                                   stelltype = sok.recv(2)
                                   stelltime = sok.recv(8)
                                   stellrab  = sok.recv(4)
                                   stelldecb = sok.recv(4)
                                   print(stelltype+stelltime+stellrab+stelldecb)
                                   stellra   = struct.unpack('<I',stellrab)[0]
                                   stelldec  = struct.unpack('<i',stelldecb)[0]
                                   stellpos = radec.RADec.fromStellarium(stellra,stelldec)
                                   if sok in self.gotoportlist:
                                        gotopos = stellpos
                                   elif sok in self.syncportlist:
                                        syncpos = stellpos
                                   else:
                                        print("Not sure whether to sync or goto.")
                              else:
                                   print("Stellarium says it's sending ",leng,"bytes.  I don't even...")               
          return gotopos,syncpos
     
     def send(self,pos,type='GOTO'):
          if len(self.gotoportlist) > 0:
               stellpos = pos.toStellarium()
               """ compose message.  Stellarium data format:
               2bytes              # bytes in msg
               2bytes              type = 0 
               8bytes              Time (microseconds since epoch)
               4bytes              RA
               4bytes              Dec
               4bytes              Status (0 = OK)"""
               bytestream = struct.pack('<H',0) + \
                          struct.pack('<Q',int(time.time()*1e6))+\
                          struct.pack('<I',stellpos[0])+\
                          struct.pack('<i',stellpos[1])+\
                          struct.pack('<I',0)                            
               bytestream = struct.pack('<H',len(bytestream)+2)+bytestream  # prepend length
               if type=='SYNC':
                    ready_to_read, ready_to_write, in_error = select.select(self.syncportlist,self.syncportlist,self.syncportlist,0)
               else:
                    ready_to_read, ready_to_write, in_error = select.select(self.gotoportlist,self.gotoportlist,self.gotoportlist,0)
               for sok in ready_to_write:
                    sok.send(bytestream)
     
