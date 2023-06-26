HOW TO DECODE STRIDR DATA
=========================

First, this depends strongly on how the data is acquired. The multiple approaches include...

 - Run an Iridium SBD receiver
 - Emails with SBD attachments
 - Hosted Iridium service (have not tried this yet)

Iridium SBD Receiver
--------------------
This will not run on the Arete network because it requires an open port to the outside world. It is
called directip and runs either on its own or in a Docker container.

The files are named in a consistent convention in the format (something like, I probably got the
format characters wrong) %Y%M%D%h%m%s-imei-message_order.sbd

The imei is of course the modem IMEI, and the message order is a sequential identifier indiciating
the order the receiver received this message. It is not the MOMSN, that is inside the packet. The
files are a binary format which are easily decoded using the directip isbd.py functions.

If the volume mount is not properly configured it will store data internally. To retreive it, e.g.
```
docker cp confident_mclaren:/home/jim/sbd_data /home/jim
```

These files contain an Iridium header. It contains some interesting and potentially useful and
equipotentially useless data. You will want to strip it off before trying to send data to the
decoder. The following snippet can be run as a script to take a given Iridium file and create an
output (test.sbd) which can later be handed off to the decoder.

```
#!/usr/bin/env python3

import subprocess
import sys
import isbd

sbd_filename = sys.argv[-1]

i = isbd.Isbdmsg()
i.read_sbd_file(sbd_filename)

payload = i.payload

with open('test.sbd', 'wb') as fout:
    for x in payload:
                fout.write(x)
```

Then tar the data up and copy it to a machine running the decoder.


Emails with SBD attachments
---------------------------
These are more annoying because you have to manually deal with each one. Copy the files out of
Outlook and put them somewhere you can work with them. These files are named in the format
imei_momsn.sbd, where the momsn is zero-padded to 6 digits long.


Standing up the decoder
-----------------------
The decoder was originally written to run in a Docker container. We do not seem to have access to
those so instead I am using one of the dcam machines to host it. You need to be able to open a
network port as a server, which should work fine on a windows box too, but then you have to deal
with windowsy stuff.

I made rough notes on how to do this while I was doing it. A person who understands linux and python
will have an easier time repeating this, and should document a little better next time and clean up
these notes.

1. Clone the STRIDR repo
```git clone https://bitbucket.corp.arete.com:8443/scm/~jfriel/stridr.git```
2. For some reason stridr wants to be STRIDR so make a link. This command might be backwards, I do
that sometimes.
```ln -s STRIDR stridr```
3. Create a new environment. This uses anaconda, but you could do it without. Make sure to install
the python packages listed in requirements.txt. Maybe this command is messed up a little, if so,
just make the environment and then use pip to install the requirements.
```conda create -n stridr -r stridr/requirements.txt```
4. You also need to install crcmod. Not sure why that did not make it into the requirements.
```pip install crcmod```
5. Create a new screen so this keeps running for you, otherwise you will have to keep restarting the
decoder every time you log out. Maybe that is okay for you. Look up GNU screen for how to use it.
Hint: Ctrl-A, d will disconnect from a running screen session, and you can reconnect to it by
running screen -r stridr.
```screen -S stridr```
6. Now recreate the config database.
```cat stridr/scripts/resources/sqlite_dump_something.txt | sqlite3 /home/jfriel/config.db```
7. Edit handle_messages to point to the config db you just created. Look in
stridr/services/satcom/handle_messages.py and edit CONFIG_DB to point to /home/jfriel/config.db or
wherever you put it in the previous step.
8. Finally, run the service to host the decoder.
```python3 stridr/comms/flask_interface.py```

If it sits there and does nothing, congratulations, you have stood up the decoder. Hooray.


Sending packets to the decoder
------------------------------
IFF the decoder is running, and is running on the same machine as you are running the following
code, this should just work. If not, you will have to make the obvious changes.

The short of it is, run the following command:
```curl --header "Content-Type:application/octet-stream" --data-binary @test.sbd http://localhost:5000/arete/packet```

You will replace test.sbd with the path to the correct sbd file you wish to decode.

So, for an Iridium SBD receiver data file, containing the full Iridium header/wrapper around the
STRIDR payload, you could run a script like the following to completely decode:
```
#!/usr/bin/env python3

import subprocess
import sys
import isbd

sbd_filename = sys.argv[-1]

i = isbd.Isbdmsg()
i.read_sbd_file(sbd_filename)

payload = i.payload

with open('test.sbd', 'wb') as fout:
    for x in payload:
        fout.write(x)

        subprocess.Popen('curl --header "Content-Type:application/octet-stream" --data-binary @test.sbd http://localhost:5000/arete/packet', shell=True).wait()
        print()
```

Here are a few functions you can use for similar work. Rather than using subprocess to run curl,
messages are sent to the decoder using the python standard urllib3 library.

```
import isbd
import urllib3
import json

def readFile(sbd_filename):
    '''
    Reads an Iridium datafile. These files are output from the directip receiver.
    There are many fields in 'i', including imei, a timestamp, and an estimate of
    lat/lon of the transmitter, which is usually not very good.
    The Arete payload is in i.payload.
    '''
    i = isbd.Isbdmsg()
    i.read_sbd_file(sbd_filename)
    return i

def fileToJson(payload):
    '''
    Takes an Arete payload and decodes it to json, returns a json object.
    '''
    http = urllib3.PoolManager()
    response = http.request('POST', 'http://localhost:5000/arete/packet', body=payload, headers={'Content-Type':'application/octet-stream'})
    j = json.loads(response.data)
    return j
```
