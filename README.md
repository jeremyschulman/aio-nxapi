# Cisco NX-API asyncio Client

This repository contains a Cisco NX-API asyncio based client that uses
the [httpx](https://www.python-httpx.org/) as an underlying transport and
[lxml](https://lxml.de/) as the basis for handling XML.

Note: This client does not support the NETCONF interface.

**WORK IN PROGESS**

### Quick Example

Thie following shows how to create a Device instance and run a list of
commands.

By default the Device instance will use HTTPS transport.  The Device instance
supports the following settings:

   * `host` - The device hostname or IP address
   * `username` - The login user-name
   * `password` - The login password
   * `proto` - *(Optional)* Choose either "https" or "http", defaults to "https"
   * `port` - *(Optional)* Chose the protocol port to override proto default

The result of command execution is a list of CommandResults (namedtuple).
The `output` field will be:
   * lxml.Element when output format is 'xml'
   * dict when output format is 'json'
   * str when output format is 'text'

```python
from asyncnxapi import Device

username = 'dummy-user'
password = 'dummy-password'

async def run_test(host):
    dev = Device(host=host, creds=(username, password))
    res = await dev.exec(['show hostname', 'show version'], ofmt='json')
    for cmd in res:
       if not cmd.ok:
          print(f"{cmd.command} failed")
          continue

       # do something with cmd.output as dict since ofmt was 'json'
```

# Limitations

  * Chunking is not currently supported.  If anyone has need of this feature
  please open an issue requesting support.

# References

Cisco DevNet NX-API Rerefence:<br/>
   * https://developer.cisco.com/site/cisco-nexus-nx-api-references/

Cisco platform specific NX-API references:

   * N3K systems, requires 7.0(3)I2(2) or later:
    https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus3000/sw/programmability/7_x/b_Cisco_Nexus_3000_Series_NX-OS_Programmability_Guide_7x/b_Cisco_Nexus_3000_Series_NX-OS_Programmability_Guide_7x_chapter_010010.html

   * N5K system, requires 7.3(0)N1(1) or later:
    https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus5000/sw/programmability/guide/b_Cisco_Nexus_5K6K_Series_NX-OS_Programmability_Guide/nx_api.html#topic_D110A801F14F43F385A90DE14293BA46

   * N7K systems:
    https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus7000/sw/programmability/guide/b_Cisco_Nexus_7000_Series_NX-OS_Programmability_Guide/b_Cisco_Nexus_7000_Series_NX-OS_Programmability_Guide_chapter_0101.html

   * N9K systems:
    https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/6-x/programmability/guide/b_Cisco_Nexus_9000_Series_NX-OS_Programmability_Guide/b_Cisco_Nexus_9000_Series_NX-OS_Programmability_Guide_chapter_011.html
