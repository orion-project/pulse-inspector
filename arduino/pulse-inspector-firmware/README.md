# pulse-inspector-firmware

This is a test sketch that allows basic autocorrelator functionality. It is based on the emulator dummy and probably needs some major revisions before it can be considered operational.

What works kind of:
* homing
* jogging 
* moving
* single scan

Note about the scan: For now a scan starts in the center of the scan range. The stage will move to one end of the range, scan the full range and transmit the measured values and finally return to the center again. The reason for this is that I want to see the maximum of the AC signal physically in the lab when I start the scan. Additionally the stages I tested have quite some backlash --> The center of the scan will be shifted in the forward and backward direction. I consider this a low priority, it will only give me a factor two in scan rate and cause quite some headache

The LCD screen functionality is disabled as it is not present on my test board. 
