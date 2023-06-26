The STRIDR devices attempt to connect to a wireless network on boot. They will connect to either an OOT or an OOT2 network if one is available. The devices will only connect when they are powered on, and will, within 3 minutes, typically power back off unless you do something to keep them awake.

To set up an OOT network use the following settings:

SSID:		OOT (or OOT2)
Security:	WPA2
Passphrase:	OOTProjectIn2019

To connect to the OOT network:
1.	Enable wifi
2.	Connect to the SSID:   ```OOT```
3.	Use the WPA2 password:  ```OOTProjectIn2019```
4.	You are connected

STRIDR devices each use DHCP to obtain a new address, so occasionally they do change. The STRIDR_tools/wifi_tools/oot_ssh_status.py tool from the other repository can tell you the IP addresses of any OOT devices on the network. 

STRIDR is supposed to be an autonomous buoy which turns itself on and off on its own schedule. It’s configured to turn on every 15 minutes. You’ll want to connect immediately after it boots. It takes 40-60 seconds from power on to be available on the network again, and hopefully at the same IP address. Log in and immediately run the following command:

```touch /tmp/debug_stay_awake```

That will create a file which prevents the watchdog from shutting the system down. If that file does not exist, either the acquisition/processing code will terminate abnormally (takes up to 3 minutes after startup), normally (typically takes between 3-5 minutes after powerup), or the watchdog will kill everything (takes 8 minutes after startup). STRIDR will repeat 15 minute cycles from startup to startup.
