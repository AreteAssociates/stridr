This note describes how to connect to the OOT network. OOT is a wireless network IT configured for us to enable development of the STRIDR program. It is really important that you disconnect the Ethernet plug from your computer prior to connecting to it. That means you won’t be able to check email at the same time (unless you use the VPN, I guess, not sure) as you are connected to an OOT device.

For your future reference, OOT is the DARPA program Oceans of Things that we worked on in 2019 for which we built 1500 STRIDR devices. A complete STRIDR is waterproofed in a round pressure vessel, has a glass top which protects the antennas and a few sensors, and 4 folding floats covered in solar panels. The floats are made of wood, which - I am not making this up - are cut and painted for us by the Amish.

To connect to the OOT network:
1.	Disconnect the Ethernet plug to the corporate network from your PC/laptop
2.	Enable wifi
3.	Connect to the SSID:   ```OOT```
4.	Use the WPA2 password:  ```OOTProjectIn2019```
5.	You are connected

The OOT network appears to use 192.168.50.0/24. There are several devices on this network, I don’t know what they all are. STRIDR devices each use DHCP to obtain a new address, so occasionally they do change. The STRIDR_tools/wifi_tools/oot_ssh_status.py tool from the other repository can tell you the IP addresses of any OOT devices on the network. As of 19 February 2020, the debug unit on my desk can be found at:

- 192.168.50.62
- Username:    oot
- Password:     Liberty1Witch

If you can get on the device, just don’t reboot it. STRIDR is supposed to be an autonomous buoy which turns itself on and off on its own schedule. It’s configured to turn on every 15 minutes. If you do happen to reboot it, I can fix it later, just let me know. If you feel adventuresome, then go nuts, reboot it. You’ll want to connect immediately. From the time you hit enter after hitting reboot, it should take 40-60 seconds to be available on the network again, and hopefully at the same IP address. Log in and immediately run the following command:

```touch /tmp/debug_stay_awake```

That will create a file which prevents the watchdog from shutting the system down. If that file does not exist, either the acquisition/processing code will terminate abnormally (takes up to 3 minutes after startup), normally (typically takes between 3-5 minutes after powerup), or the watchdog will kill everything (takes 8 minutes after startup). STRIDR will repeat 15 minute cycles from startup to startup.
