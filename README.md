# Cisco NX-API asyncio Client

This repository contains a Cisco NX-API asyncio based client that uses
the [httpx](https://www.python-httpx.org/) as an underlying transport and
[lxml](https://lxml.de/) as the basis for handling XML.

**WORK IN PROGESS**

### Quick Example

Thie following shows how to create a Device instance and run a list of
commands.  The result of command execution is a list of 

```python
from asyncnxapi import Device, CommandResults

username = 'dummy-user'
password = 'dummy-password'

async def run_test(host, port=None):
    dev = Device(host=host, creds=(username, password), port=port)
    res = await dev.exec(['show hostname', 'show version'])
    for cmd in res:
       if not cmd.ok:
          print(f"{cmd.command} failed")
          continue

       # do something with cmd.results, which is an lxml.Element instance.
```