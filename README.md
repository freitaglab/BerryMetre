# BerryCells for Berry Future
## Overview
The BerryMetre is an open source solar simulator for small solar cells, which has been developed for the Royal Society Summer Science Exhibition 2022. Children (and interested adults) fabricate a
small working dye-sensitised solar cell (DSC) using conductive glass, titanium dioxide, and berry juice (which acts as a dye to absorb the light). The solar cell is then measured using the
BerryMetre, and the J-V-curce, as well as power output including maximum power point (MPP) are displayed in real-time on a big screen. By increasing and decreasing the light intensity, or just by
covering the solar cell with their hands, the students immediately see the effect on the generated current and power. To "certify" the fabricated solar cell, the student presses a big red button and 
an image of the characterisation is uploaded to the internet, the results are being tweeted, and a sticker with a QR-code link to the result is printed. This way, the students can learn more about 
the importance of solar cells, and show the results to their friends and family. And to be honest: Everybody loves stickers!    

## Technical Summary
The core component, which is the BerryMetre itself, uses an Arduino Pro Mini 5V to periodically cycle through an array of load resistors, to simulate a realistic load of the measured solar cell. 
The solar cell voltages under are measured at one of the analogue pin, and together with the knowledge of the resitors, both the J-V-curve and power generation of the solar cell including its
maximum power point (MPP) can calculated.
The Arduino Pro Mini communicates via serial communication with a Wemos D1 Mini, which acts as a UDP relay to send the data to any receiver via regular WiFi. The receiver has been implemented
in Python and uses Matplotlib for real-time visualization of the J-V-curve and power generation. It takes care of tweeting the results, cloud communication, and sticker printing.

## Read the Wiki
Head over to the [Wiki](../../wiki) to learn more about
* Hardware components
* Printing stickers
* Wireless setup
* Gesture controlling a lamp using a Leap motion controller
* And more...

## Licenses
- GNU AFFERO GENERAL PUBLIC LICENSE v3.0 - used for source code developed for the BerryMetre
- Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) - used for design and related files of the PCBs 
