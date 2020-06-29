# Cisco NX-API asyncio Client

This repository contains a Cisco NX-API asyncio based client that uses
the [httpx](https://www.python-httpx.org/) as an underlying transport and
[lxml](https://lxml.de/) as the basis for handling XML.

**WORK IN PROGESS**

### Quick Example

Thie following shows how to create a Device instance and run a list of
commands.  The result of command execution is a list of CommandResults (namedtuple).

By default the Device instance will use HTTPS transport.  The Device instance
supports the following settings:

   * `host` - The device hostname or IP address
   * `username` - The login user-name
   * `password` - The login password
   * `proto` - *(Optional)* Choose either "https" or "http", defaults to "https"
   * `port` - *(Optional)* Chose the protocol port to override proto default

```python
from asyncnxapi import Device

username = 'dummy-user'
password = 'dummy-password'

async def run_test(host):
    dev = Device(host=host, creds=(username, password))
    res = await dev.exec(['show hostname', 'show version'])
    for cmd in res:
       if not cmd.ok:
          print(f"{cmd.command} failed")
          continue

       # do something with cmd.results, which is an lxml.Element instance.
```