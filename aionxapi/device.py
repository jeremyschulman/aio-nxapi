"""
This module provides the asyncio client for Cisco NX-API, expected to work on:
    * N3K system
    * N5K system  (tested)
    * N7K system
    * N9K system
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List, AnyStr
import asyncio
import json
from socket import getservbyname
import ssl

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import httpx

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from asyncnxapi import xmlhelp


__all__ = ["Device"]

_ssl_context = ssl.create_default_context()
_ssl_context.options &= ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
_ssl_context.minimum_version = ssl.TLSVersion.TLSv1
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE
_ssl_context.set_ciphers("HIGH:!DH:!aNULL")

# _ssl_context = ssl.SSLContext(ssl_version=ssl.PROTOCOL_TLSv1_1)  # noqa

# _ssl_context = ssl.create_default_context()
# # Sets up old and insecure TLSv1.
# _ssl_context.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
# _ssl_context.minimum_version = ssl.TLSVersion.TLSv1


_NXAPI_CMD_TEMPLATE = """\
<?xml version="1.0"?>
<ins_api>
<version>{api_ver}</version>
<type>{cmd_type}</type>
<chunk>{chunk}</chunk>
<sid>{sid}</sid>
<input>{cmd_input}</input>
<output_format>{ofmt}</output_format>
</ins_api>"""


class Device(httpx.AsyncClient):
    auth: httpx.Auth = None

    DEFAULT_TIMEOUT = 60
    CMDTYPES_OPTIONS = ("cli_show", "cli_show_ascii", "cli_conf", "bash")
    OFMT_OPTIONS = ("xml", "json", "text")
    API_VER = "1.0"

    def __init__(
        self,
        host: Optional[str] = None,
        proto: Optional[str] = "https",
        port: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):
        self.port = port or getservbyname(proto)
        self.host = host

        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)

        if username and password:
            self.auth = httpx.BasicAuth(username, password)

        kwargs.setdefault("auth", self.auth)

        if not kwargs["auth"]:
            raise ValueError("Missing required authentication")

        kwargs.setdefault("base_url", f"{proto}://{host}:{self.port}")
        kwargs.setdefault("verify", _ssl_context)

        super(Device, self).__init__(**kwargs)

        self.headers["Content-Type"] = "application/xml"
        self.cmd_type = "cli_show"
        self.ofmt = "xml"

    def nxapi_command(self, cmd_input, formatting, sid=None):
        cmd_type = formatting.setdefault("cmd_type", self.cmd_type)
        ofmt = formatting.setdefault("ofmt", self.ofmt)

        return _NXAPI_CMD_TEMPLATE.format(
            api_ver=self.API_VER,
            cmd_type=cmd_type or self.cmd_type,
            cmd_input=cmd_input,
            chunk=0,
            sid=sid or "sid",
            ofmt=ofmt or self.ofmt,
        )

    async def nxapi_exec(self, xcmd, formatting, strip_ns=False):
        res = await self.post("/ins", data=xcmd)
        res.raise_for_status()

        if formatting["ofmt"] == "json":
            as_json = json.loads(res.text)

            outputs = as_json["ins_api"]["outputs"]["output"]
            if not isinstance(outputs, list):
                outputs = [outputs]

            # if the command results are empty then there is no 'body' in the
            # response dictionary.  in this case a return value of None
            # indicates this condition to the Caller.

            return [cmd_res.get("body") for cmd_res in outputs]

        # Output format is "xml" or "text"; but in either case the body content
        # is extracted in the same manner.

        as_text = xmlhelp.strip_ns(res.text) if strip_ns else res.text
        as_xml = xmlhelp.fromstring(as_text)

        if cli_errors := as_xml.findall(".//clierror"):
            raise RuntimeError(cli_errors)

        def body_is_text(_res_e):
            return _res_e.find("body").text.strip()

        def body_is_xml(_res):
            return _res.find("body")

        get_output = (
            body_is_text if formatting["cmd_type"] == "cli_show_ascii" else body_is_xml
        )

        return [get_output(cmd_res) for cmd_res in as_xml.xpath("outputs/output")]

    async def cli(
        self,
        command: Optional[AnyStr] = None,
        commands: Optional[List[AnyStr]] = None,
        ofmt: Optional[AnyStr] = None,
        strip_ns: Optional[bool] = False,
    ):
        if not any((command, commands)):
            raise RuntimeError("Required 'command' or 'commands'")

        formatting = dict(ofmt=ofmt or self.ofmt)

        if ofmt == "text":
            formatting["cmd_type"] = "cli_show_ascii"
            formatting["ofmt"] = "xml"

        nxapi_cmd = self.nxapi_command(
            " ;".join([command] if command else commands), formatting
        )
        res = await self.nxapi_exec(nxapi_cmd, formatting=formatting, strip_ns=strip_ns)
        return res[0] if command else res

    async def check_connection(self) -> bool:
        """
        This function checks the target device to ensure that the NXAPI port is
        open and accepting connections.  It is recommended that a Caller checks
        the connection before involing cli commands, but this step is not
        required.

        Returns
        -------
        True when the device NXAPI is accessible, False otherwise.
        """
        try:
            await asyncio.open_connection(self.host, port=self.port)
        except OSError:
            return False
        return True

    # async def nxapi_write_config(self, xcmd):
    #     """
    #     This coroutine is used to push the configuration to the device and
    #     return any error XML elements.  If no errors then return value is None.
    #     """
    #     res = await self.post("/ins", data=xcmd)
    #     res.raise_for_status()
    #     as_xml = xmlhelp.fromstring(res.text)
    #
    #     if any_errs := as_xml.xpath(".//code[. != '200']"):
    #         return any_errs
    #
    #     return None
