# Import
import c4d
from c4d import gui,plugins

import os
import math
import re
import socket
import select
import string
import struct
import sys
import threading
import time
import types

# Plugin Info
PLUGIN_ID = 1030663
PLUGIN_NAME = "fOSC"
PLUGIN_DESCRIPTION = ""
# UI
CONTAINER_NAME = "fOSC-Container"
DIALOG_SIZE_WIDTH  = 300
DIALOG_SIZE_HEIGHT =  80
# UI - Buttons
UI_PORT = 1001
UI_CREATE = 1002
UI_RUNBUTTON = 1003
UI_RECORD = 1004
UI_STOPBUTTON = 1005
UI_AUTOMAP = 1006
# Server Info
IP_ADDRESS = "localhost"
DEFAULT_PORT = 7000

class OSC():
    @staticmethod
    def readByte(data):
        length   = data.find(b'\x00')
        nextData = int(math.ceil((length+1) / 4.0) * 4)
        return (data[0:length], data[nextData:])

    @staticmethod
    def readString(data):
        length   = str(data).find("\0")
        nextData = int(math.ceil((length+1) / 4.0) * 4)
        return (data[0:length], data[nextData:])
    
    @staticmethod
    def readBlob(data):
        length   = struct.unpack(">i", data[0:4])[0]
        nextData = int(math.ceil((length) / 4.0) * 4) + 4
        return (data[4:length+4], data[nextData:])
    
    @staticmethod
    def readInt(data):
        if(len(data)<4):
            print("Error: too few bytes for int", data, len(data))
            rest = data
            integer = 0
        else:
            integer = struct.unpack(">i", data[0:4])[0]
            rest    = data[4:]
    
        return (integer, rest)
    
    @staticmethod
    def readLong(data):
        """Tries to interpret the next 8 bytes of the data
        as a 64-bit signed integer."""
        high, low = struct.unpack(">ll", data[0:8])
        big = (long(high) << 32) + low
        rest = data[8:]
        return (big, rest)
    
    @staticmethod
    def readDouble(data):
        """Tries to interpret the next 8 bytes of the data
        as a 64-bit double float."""
        floater = struct.unpack(">d", data[0:8])
        big = float(floater[0])
        rest = data[8:]
        return (big, rest)

    @staticmethod
    def readFloat(data):
        if(len(data)<4):
            print("Error: too few bytes for float", data, len(data))
            rest = data
            float = 0
        else:
            float = struct.unpack(">f", data[0:4])[0]
            rest  = data[4:]
    
        return (float, rest)

    @staticmethod
    def readTimeTag(data):
        """
        Tries to interpret the next 8 bytes of the data as a TimeTag.
        """
        high, low = struct.unpack(">ll", data[0:8])
        if (high == 0) and (low <= 1):
            time = 0.0
        else:
            time = int(high) + float(low / 1e9)
        rest = data[8:]
        return (time, rest)

    @staticmethod
    def decodeOSC(data):
        """
        Converts a binary OSC message to a Python list. 
        """

        table = { "i" : OSC.readInt, "f" : OSC.readFloat, "s" : OSC.readString, "b" : OSC.readBlob, "d" : OSC.readDouble }
        decoded = []
        address, rest = OSC.readString(data)

        if address.startswith(","):
            typetags = address
            address = ""
        else:
            typetags = ""
        
        if address == "#bundle":
            
            time, rest = OSC.readTimeTag(rest)
            decoded.append(address)
            decoded.append(time)
            
            while len(rest)>0:
                length, rest = OSC.readInt(rest)
                decoded.append(OSC.decodeOSC(rest[:length]))
                rest = rest[length:]
    
        elif len(rest) > 0:

            if not len(typetags):
                typetags, rest = OSC.readString(rest)

            decoded.append(address)
            decoded.append(typetags)

            if typetags.startswith(","):
                for tag in typetags[1:]:
                    value, rest = table[tag](rest)
                    decoded.append(value)
            else:
                print "OSCMessage's typetag-string lacks the magic ',' "

        return decoded

class OSCReceiver():
    def run(self, create, record):
        
        osc_dict = {}
        
        def write( key , value , table):
            value.extend( [0,0,0,0,0,0] )
            table[ key ] = value

        # Looping section for reading data & write to the _osc_dict_ variable.
        while(True):

            try:
                data = self.sock.recv(1024)
            except:
                # break if nothing received
                break

            decoded = OSC.decodeOSC(data)
            # format: [#bundle, timetag, msg...]
            if decoded[0] == "#bundle" :
                msgs = decoded[ 2 : ]
                for i in msgs:
                    write( i[0] , i[ 2 : 8 ] , osc_dict )
            else:
                write( decoded[0] , decoded[ 2 : 8 ] , osc_dict )

        # Find the target object.
        doc = c4d.documents.GetActiveDocument()
        
        for key, value in osc_dict.items():
            
            # Search for object with the name.
            obj = doc.SearchObject(key)
            
            if obj is None and create:
                
                container = self.getContainer();
                obj = c4d.BaseObject( c4d.Onull )

                obj.SetName( key )
                obj.InsertUnder( container )
            
            # Set position & rotation from decoded data.
            if obj is not None:
                pos = c4d.Vector( value[0] , value[1] , value[2] )
                rot = c4d.Vector( math.radians(value[3]) ,  math.radians(value[4]) ,  math.radians(value[5]) )
                obj.SetRelPos(pos)
                obj.SetRelRot(rot)
                if record: self.setKey(obj, pos, rot)
        
        # Commit the changes
        c4d.EventAdd()

    def __init__(self, UDP_PORT):
        self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(0)
        self.sock.bind( (IP_ADDRESS, UDP_PORT) )
        
    def __del__(self):
        self.sock.close()

    def getContainer(self):
        doc = c4d.documents.GetActiveDocument()
        container = doc.SearchObject(CONTAINER_NAME)
        # If none, make a container.
        if container is None:
            container = c4d.BaseObject(c4d.Onull)
            container.SetName(CONTAINER_NAME)
            doc.InsertObject(container)
            c4d.EventAdd()

        return container

    def setKey( self, obj , pos , rot ):
        
        def getTrack( o , desc ):
            track = o.FindCTrack( desc )
            if not track:
                track = c4d.CTrack( o , desc )
                o.InsertTrackSorted( track )
            return track
        
        def setKeyValue(trk, time, val):
            curve = trk.GetCurve()
            key = curve.AddKey(t)['key']
            key.SetValue( curve , val )

        # Get Position Tracks
        rel_pos = c4d.DescLevel( c4d.ID_BASEOBJECT_REL_POSITION , c4d.DTYPE_VECTOR , 0 )
        tPosX = getTrack( obj , c4d.DescID( rel_pos , c4d.DescLevel( c4d.VECTOR_X , 0 ) ) )
        tPosY = getTrack( obj , c4d.DescID( rel_pos , c4d.DescLevel( c4d.VECTOR_Y , 0 ) ) )
        tPosZ = getTrack( obj , c4d.DescID( rel_pos , c4d.DescLevel( c4d.VECTOR_Z , 0 ) ) )
        # Get Rotation Tracks
        rel_rot = c4d.DescLevel( c4d.ID_BASEOBJECT_REL_ROTATION , c4d.DTYPE_VECTOR , 0 )
        tRotH = getTrack( obj , c4d.DescID( rel_rot , c4d.DescLevel( c4d.VECTOR_X , 0 ) ) )
        tRotP = getTrack( obj , c4d.DescID( rel_rot , c4d.DescLevel( c4d.VECTOR_Y , 0 ) ) )
        tRotB = getTrack( obj , c4d.DescID( rel_rot , c4d.DescLevel( c4d.VECTOR_Z , 0 ) ) )

        # Call that function
        doc = c4d.documents.GetActiveDocument()
        t = doc.GetTime()
        setKeyValue( tPosX , t , pos.x )
        setKeyValue( tPosY , t , pos.y )
        setKeyValue( tPosZ , t , pos.z )
        setKeyValue( tRotH , t , rot.x )
        setKeyValue( tRotP , t , rot.y )
        setKeyValue( tRotB , t , rot.z )

        return True

    @staticmethod
    def startServer(self):
        if self.ServerStarted == False:
            try:
                # init a OSCReceiver object
                self.receiver = OSCReceiver(self.Port)
                if self.RecordMessage:
                    c4d.CallCommand(12412) # Play Forwards
            except Exception as inst:
                print "error setting up receiver"
                print type(inst)
                print inst
                return
            self.SetTimer(10)
            self.updateInterface()
            self.ServerStarted = True
    
    @staticmethod
    def stopServer(self):
        if self.ServerStarted:
            try:
                # Every time the server is stopped, 
                # the receiver object is deleted.
                # (call __del__ in OSCReceiver)
                del self.receiver
                if self.RecordMessage:
                    c4d.CallCommand(12412) # Play Forwards (this command is a toggle, call again to pause the playback)
            except Exception as inst:
                print "error deleting receiver, it may not exist. Check the setup function and runtime functions. "
                print type(inst)
                print inst
            self.SetTimer(0)
            self.updateInterface()
            self.ServerStarted = False

class OSCDialog(c4d.gui.GeDialog):
    def CreateLayout(self):
        
        # Variables
        row_height   = 20
        groupElement_flags = c4d.BFH_LEFT|c4d.BFV_CENTER
        
        # Lambdas
        self.AddEmpty = lambda: self.AddStaticText(0,0,0,0," ")
        self.AddHeader = lambda (text): self.AddStaticText(
            id    = 0,
            flags = c4d.BFH_LEFT|c4d.BFV_CENTER,
            initw = 150,
            inith = row_height,
            name  = text
        )
        self.AddFelx = lambda: self.AddStaticText(id=0,flags=c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT,name="")
        
        # Build
        self.SetTitle(PLUGIN_NAME)
        
        self.AddFelx()
        self.GroupBegin(
            id    = 0,
            flags = 0,
            cols  = 3,
            rows  = 4,
            title = "",
            groupflags = c4d.BFV_GRIDGROUP_EQUALROWS
        )
        # Title Line
        self.AddHeader("fOSC v1.1.1")
        self.AddEmpty()
        self.AddEmpty()
        # C4D Commands
        self.AddHeader("Options: ")
        self.AddCheckbox(
            id = UI_CREATE,
            flags = groupElement_flags,
            initw = 200,
            inith = row_height,
            name = "Create Nulls Objects"
        )
        self.AddCheckbox(
            id = UI_RECORD,
            flags = groupElement_flags,
            initw = 200,
            inith = row_height,
            name = "Record Incoming Data"
        )
        # Server Command
        self.AddHeader("OSC Server: ")
        self.runButton  = self.AddButton(
            id    = UI_RUNBUTTON,
            flags = groupElement_flags,
            initw = 140,
            inith =  15,
            name  = "Start Listening"
        )
        self.stopButton  = self.AddButton(
            id    = UI_STOPBUTTON,
            flags = groupElement_flags,
            initw = 140,
            inith =  15,
            name  = "Stop Listening"
        )
        # Server Options
        self.AddHeader("Listening to Port: ")
        self.portNumber = self.AddEditNumberArrows(
            id    = UI_PORT,
            flags = groupElement_flags
        )
        self.GroupEnd()

        self.AddEmpty()

        self.GroupBegin(
            id    = 2,
            flags = 0,
            cols  = 1,
            rows  = 2,
            title = "notes",
            groupflags = c4d.BFV_GRIDGROUP_EQUALROWS
        )
        self.AddStaticText(
            id    = 0, 
            flags = c4d.BFH_LEFT|c4d.BFV_CENTER,
            name  = "Note: Closing the dialog will stop the receiver. "
        )
        self.AddStaticText(
            id    = 0, 
            flags = c4d.BFH_LEFT|c4d.BFV_CENTER,
            name  = "Check: https://github.com/fillmember/fosc"
        )
        self.GroupEnd()

        self.AddFelx()

        return True

    def InitValues(self):
        # This function is called by C4D everytime GUI is created. 
        
        # Configure to server On/Off buttons / or set up ServerStarted
        try:
            if self.ServerStarted :
                self.Enable(self.portNumber, False)
                self.Enable(self.runButton, False)
                self.Enable(self.stopButton, True)
            else :
                self.Enable(self.runButton, True)
                self.Enable(self.stopButton, False)
        except:
            self.ServerStarted = False
            self.Enable(self.runButton, True)
            self.Enable(self.stopButton, False)

        # Configure to create /or/ set up property
        try:
            self.SetBool(UI_CREATE, self.NullCreating)
        except:
            self.NullCreating = self.GetBool(UI_CREATE)
        
        try:
            self.SetBool(UI_RECORD, self.RecordMessage)
        except:
            self.RecordMessage = self.GetBool(UI_RECORD)
        
        try:
            self.SetLong(UI_PORT, self.Port)
        except:
            self.SetLong(UI_PORT, DEFAULT_PORT, 1)
            self.Port = DEFAULT_PORT

        return True

    def Command(self, id, msg):
        # This function is called by C4D.
        if   id == UI_RUNBUTTON :
            OSCReceiver.startServer(self)
        elif id == UI_STOPBUTTON : 
            OSCReceiver.stopServer(self)
        elif id == UI_RECORD :
            self.RecordMessage = self.GetBool(UI_RECORD)
        elif id == UI_CREATE :
            self.NullCreating  = self.GetBool(UI_CREATE)
        elif id == UI_PORT :
            self.Port = self.GetLong(UI_PORT)
        else :
            print("Command(): unrecognized id received -> "+str(id))
        return True

    def Timer(self, msg):
        try:
            self.receiver.run(self.NullCreating, self.RecordMessage)
        except:
            OSCReceiver.stopServer(self)

    def updateInterface(self):
        # serverStarted & disable/enable some UIs
        if self.ServerStarted:
            self.Enable(self.portNumber, True)
            self.Enable(self.runButton, True)
            self.Enable(self.stopButton, False)
        else:
            self.Enable(self.portNumber, False)
            self.Enable(self.runButton, False)
            self.Enable(self.stopButton, True)

class fOSC(c4d.plugins.CommandData):
    def Execute(self, doc):
        if hasattr(self, 'dialog') == False:
            # init a OSCDialog object
            self.dialog = OSCDialog()

        return self.dialog.Open(
                 dlgtype=c4d.DLG_TYPE_ASYNC
                ,pluginid=PLUGIN_ID
                ,defaultw=DIALOG_SIZE_WIDTH
                ,defaulth=DIALOG_SIZE_HEIGHT
               )

if __name__=='__main__':
    icon = c4d.bitmaps.BaseBitmap()
    dir, file = os.path.split(__file__)
    icon.InitWith( os.path.join(dir, "res", "Icon.tif") )
    fOSC_plugin = fOSC();
    plugins.RegisterCommandPlugin(
        PLUGIN_ID
      , PLUGIN_NAME
      , 0
      , icon
      , PLUGIN_DESCRIPTION
      , fOSC_plugin
    )