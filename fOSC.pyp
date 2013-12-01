import c4d
from c4d import gui,plugins
import os
import time
import socket
import math
import struct
import OSC

# Plugin ID
PLUGIN_ID = 1030663
# UI_CONSTANTS
UI_PORT = 1001
UI_CREATE = 1002
UI_RUNBUTTON = 1003
UI_RECORD = 1004
UI_STOPBUTTON = 1005
UI_AUTOMAP = 1006
# GROUPS
GROUP_ADDRESS = 20000
GROUP_OPTIONS = 20001
GROUP_SERVERTOGGLE = 20002
#
PLUGIN_NAME = "fOSC"
PLUGIN_DESCRIPTION = ""
CONTAINER_NAME = "fOSC-Container"
IP_ADDRESS = "localhost"
DEFAULT_PORT = 7000

class OSCReceiver():
    def run(self, create, record):
        dict = {}
        # A loop of constant read.
        while(True):
            try:
                data = self.sock.recv(1024)
            except:
                break # break if nothing received
            decoded = OSC.decodeOSC(data)
            decoded.extend( [0,0,0,0,0,0] ) # exceeds 6 numbers in the list first
            dict[ decoded[0] ] = decoded[2:8] # crop to first 6 numbers
        # Find the target object.
        doc = c4d.documents.GetActiveDocument()
        for key, value in dict.items():
            # Search for object with the name.
            ob = doc.SearchObject(key)
            # Convert user's inputs here to make numbers easier to use/read in C4D, which receives radians in rotation field.
            if ob is None and create:
                container = self.getContainer();
                ob = c4d.BaseObject(c4d.Onull)
                ob.SetName(key)
                ob.InsertUnder(container)
            # Set position & rotation from decoded data.
            if ob is not None:
                pos = c4d.Vector( value[0] , value[1] , value[2] )
                rot = c4d.Vector( math.radians(value[3]) ,  math.radians(value[4]) ,  math.radians(value[5]) )
                ob.SetRelPos(pos)
                ob.SetRelRot(rot)
                if record: self.setKey(ob, pos, rot)
        c4d.EventAdd()

    def __init__(self, UDP_PORT):
        self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(0)
        self.sock.bind( (IP_ADDRESS, UDP_PORT) )
        
    def __del__(self):
        self.sock.close()

    def getContainer(self):
        # Make a container for those Nulls if one is not presented
        doc = c4d.documents.GetActiveDocument()
        container = doc.SearchObject(CONTAINER_NAME)
        if container is None:
            container = c4d.BaseObject(c4d.Onull)
            container.SetName(CONTAINER_NAME)
            doc.InsertObject(container)
            c4d.EventAdd()
        return container

    def setKey( self, obj , pos , rot ):
        def getTrack(obj, desc):
            trk = obj.FindCTrack( desc )
            if not trk:
                trk = c4d.CTrack(obj, desc)
                obj.InsertTrackSorted(trk)
            return trk
        def setKeyValue(trk, time, val):
            key = trk.GetCurve().AddKey(t)['key']
            key.SetValue(trk.GetCurve(), val)
            return True
        # Get Position Tracks
        tPosX = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_X ) )
        tPosY = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Y ) )
        tPosZ = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Z ) )
        # Get Rotation Tracks
        tRotH = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X ) )
        tRotP = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Y ) )
        tRotB = getTrack( c4d.DescID( c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z ) )
        # Call that function
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
                self.receiver = OSCReceiver(self.Port) # This is the first place we set up receiver. (call __init__ in OSCReceiver)
                if self.Recording:
                    c4d.CallCommand(12412) # Play Forwards
            except Exception as inst:
                print "error setting up receiver"
                print type(inst)
                print inst
                return # prevent this function to set up timer and such
            self.SetTimer(10)
            self.updateInterface()
            self.ServerStarted = True
    
    @staticmethod
    def stopServer(self):
        if self.ServerStarted:
            try:
                del self.receiver # Every time the server is stopped, the receiver object is deleted. (call __del__ in OSCReceiver)
                if self.Recording:
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
        # This function is called by C4D.
        self.SetTitle(PLUGIN_NAME)

        flags = c4d.BFH_SCALE|c4d.BFV_SCALE
        self.GroupBegin(GROUP_ADDRESS,c4d.BFH_SCALEFIT|c4d.BFV_FIT,3,0,"")
        self.AddStaticText(0,flags,0,0,"Listening Port",0)
        self.portNumber = self.AddEditNumberArrows(UI_PORT,flags)
        self.GroupEnd()

        #flags = c4d.BFH_SCALE|c4d.BFV_SCALE
        self.GroupBegin(GROUP_OPTIONS,c4d.BFH_SCALEFIT|c4d.BFV_FIT,2,0,"Options")
        self.AddCheckbox(UI_CREATE,flags,0,0,"Create Nulls from messages")
        self.AddCheckbox(UI_RECORD,flags,0,0,"Record data as positions")
        # self.AddCheckbox(UI_AUTOMAP,flags,0,0,"Auto Mapping (BETA)")
        self.GroupEnd()

        #flags = c4d.BFH_SCALE|c4d.BFV_SCALE
        self.GroupBegin(GROUP_SERVERTOGGLE,c4d.BFH_SCALEFIT|c4d.BFV_FIT,2,0,"")
        self.runButton = self.AddButton(UI_RUNBUTTON,flags, 150, 15, "Start Server")
        self.stopButton = self.AddButton(UI_STOPBUTTON,flags, 150, 15, "Stop Server")
        self.GroupEnd()

        self.AddStaticText(0,c4d.BFH_CENTER,0,0,"Closing the dialog will stop the receiver. ")
        
        return True

    def InitValues(self):
        # This function is called by C4D.
        # Configure to server On/Off buttons and the first chance to set up ServerStarted
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
        # Configure to create and the first chance to set up Creating
        try:
            self.SetBool(UI_CREATE, self.Creating)
        except:
            self.Creating = self.GetBool(UI_CREATE)
        # Configure to record and the first chance to set up Recording
        try:
            self.SetBool(UI_RECORD, self.Recording)
        except:
            self.Recording = self.GetBool(UI_RECORD)
        # Configure to port and the first chance to set up Port
        try:
            self.SetLong(UI_PORT, self.Port)
        except:
            self.SetLong(UI_PORT, DEFAULT_PORT, 1)
            self.Port = DEFAULT_PORT
        return True

    def Command(self, id, msg):
        # This function is called by C4D.
        if id == UI_RUNBUTTON :
            OSCReceiver.startServer(self)
        elif id == UI_STOPBUTTON : 
            OSCReceiver.stopServer(self)
        elif id == UI_RECORD :
            self.Recording = self.GetBool(UI_RECORD)
        elif id == UI_CREATE :
            self.Creating = self.GetBool(UI_CREATE)
        elif id == UI_PORT :
            self.Port = self.GetLong(UI_PORT)
        else :
            print("Command(): unrecognized id received -> "+str(id))
        return True

    def Timer(self, msg):
        try:
            self.receiver.run(self.Creating, self.Recording)
        except Exception as inst:
            print "Something went wrong when trying to do the timer function"
            print type(inst)
            print inst
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
    def Init(self, op):
        bc = op.GetData()
        op.SetData(bc)
        return True

    def Message(self, type, data):
        return True

    def Execute(self, doc):
        self.frame = doc.GetTime().GetFrame(doc.GetFps())
        if hasattr(self, 'dialog') == False:
            self.dialog = OSCDialog()

        return self.dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID, defaultw=250, defaulth=100)

if __name__=='__main__':
    bmp = c4d.bitmaps.BaseBitmap()
    dir, file = os.path.split(__file__)
    fn = os.path.join(dir, "res", "Icon.tif")
    bmp.InitWith(fn)
    result = plugins.RegisterCommandPlugin(PLUGIN_ID, PLUGIN_NAME, 0, bmp, PLUGIN_DESCRIPTION, fOSC())