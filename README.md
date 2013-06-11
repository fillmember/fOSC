# fOSC v.1
FantasticOSC, funnyOSC, futureOSC... or fillmemberOSC. 

fOSC is a Python-based plugin for CINEMA 4D users who wants to bring in creative controllers or special interactions into their animation making process. 

The plugin is based on [NIMate OSC Receiver](http://www.ni-mate.com/), while most of the codes were rewritten by [FillMember](fillmember.net) for usability and FillMember's self-learning purpose. 

I'd love to know all the comment / commitment / love / hate… on this tiny tool… Please e-mail me if you happens to be in one of above conditions. Thank you.

## Installation & Requirement
Download, and extract. Put the folder into: ~/Library/Preferences/MAXON/CINEMA 4D R1x_xxxxxxx/plugins

Tested and OK on R14. Probably on R13. 

## Nice New Features:
1. Closing the dialog window won't effect the server.
2. A container for generated nulls.
3. Every track of message can now receive up to 6 numbers in a row. And mapping them to XYZ / PHB
4. Interface, Codes are cleaned & refined & well commented. Make further improvements easier. 

## Additional Notes:
1. Numbers mapped to rotation are converted into radian, to present incoming messages in a cleaner way.
   
   For example, incoming float: 3.14159 will present as 3.14159 "degrees" in CINEMA 4D, instead of 180 degrees.
   
## Tips
1. Let fOSC create signal receiver null for you, and use "drive/driven" function to map values to desired objects. This can prevent unwanted hassles and messy animation tracks on various objects.
2. When no more new tracks are wanted, check off fOSC's create null function. 
3. When using record position function. It may not be easy to animate in realtime, try slowdown FPS in CINEMA 4D. Let expression of your controller flow and refine the curves later. 

## Resources

###Open Sound Control
OpenSoundControl.org

The protocol we loved.

###NI Mate
http://www.ni-mate.com/

Real-time motion tracking provider.

###KiCapOSC
http://www.908lab.de/?page_id=215