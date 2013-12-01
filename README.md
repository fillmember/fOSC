# fOSC v1.1
FantasticOSC, funnyOSC, futureOSC... or fillmemberOSC. 

fOSC is a Python plugin for CINEMA 4D to make special / creative controllers part of animation making process. 

The plugin is based on [NI Mate OSC Receiver](http://www.ni-mate.com/). However, most parts were rewritten by [FillMember](http://fillmember.net) for usability, stability, learning Python & for fun. 

I'd love to know all the comment / commitment / love / hate… on this tiny tool. Please e-mail me if you happens to be in one of above conditions. Thank you.

## Install
Download, and extract. Put the folder into:  
~/Library/Preferences/MAXON/CINEMA 4D R1x_xxxxxxx/plugins

Tested on R14. 

## Features:
1. A container for generated nulls.
2. Every track of message can now receive up to 6 numbers in a row. And mapping them to XYZ / PHB
3. Interface, Codes are cleaned & refined & well commented. Make further improvements easier. 
4. \#Bundle is accepted.

## Get Started

Just open fOSC dialog from plugin menu. Click start server and try send some message to it! (127.0.0.1, default port is 7000)

Every OSC message received is represented as a Null Object in C4D. 
Its position & rotation are where fOSC store incoming data. 

X -> Y -> Z -> H -> P -> B

six of them are stored in the current frame. 

## Notice:

- Each message should have 6 or less values, they can be integer or float. 7th element and later will be ignored. 

	because I havn't find a logical way to map them.
	
- Incoming message should only contains numbers ( 123 or 1.23 )

	Doesn't support string ...yet.
	
- Numbers mapped to rotation are converted for cleaner result.

	for example:

	integer 30 ---> 30 degree
	float 3.14159 ---> 3.14159 degree (instead of 180 degree)
  
## Tips
1. Let fOSC create null objects for you, and use drive/driven(XPresso) to map to target objects. This can prevent unwanted hassles and messy tracks.
2. When no new tracks are wanted, check off create null function. 
3. When using record position function. It may not be easy to animate in realtime, try slowdown FPS in CINEMA 4D. Let expression of your controller flow and refine the curve later. 

## References

* [Open Sound Control](http://OpenSoundControl.org)
* [NI Mate](http://ni-mate.com)
* [KiCapOSC](http://www.908lab.de/?page_id=215)