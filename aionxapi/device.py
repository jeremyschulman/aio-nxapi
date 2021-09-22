"""
This module provides the asyncio client for Cisco NX-API, expected to work on:
    * N3K system
    * N5K system  (tested)
    * N7K system
    * N9K system
"""

from typing import Optional, List, AnyStr
import json
from socket import getservbyname
import httpx
import ssl

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
        port = port or getservbyname(proto)

        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        kwargs.setdefault("auth", self.auth or httpx.BasicAuth(username, password))
        kwargs.setdefault('base_url', f"{proto}://{host}:{port}")
        kwargs.setdefault('verify', _ssl_context)

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

            return [cmd_res["body"] for cmd_res in outputs]

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

        formatting = dict(ofmt=ofmt)

        if ofmt == "text":
            formatting["cmd_type"] = "cli_show_ascii"
            formatting["ofmt"] = "xml"

        nxapi_cmd = self.nxapi_command(
            " ;".join([command] if command else commands), formatting
        )
        res = await self.nxapi_exec(nxapi_cmd, formatting=formatting, strip_ns=strip_ns)
        return res[0] if command else res

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


# class Device(object):
#     def __init__(
#         self,
#         host: AnyStr,
#         creds: Tuple[str, str],
#         proto: Optional[AnyStr] = "https",
#         port=None,
#         private=None
#     ):
#         self.api = Transport(host=host, creds=creds, proto=proto, port=port)
#         self.private = private
#         self.host = host
#
#     async def exec(
#         self, commands: List[AnyStr], ofmt: Optional[AnyStr] = None, strip_ns=False
#     ) -> List[CommandResults]:
#         """
#         Execute a list of operational commands and return the output as a list of CommandResults.
#         """
#         formatting = dict(ofmt=ofmt)
#
#         if ofmt == "text":
#             formatting["cmd_type"] = "cli_show_ascii"
#             formatting["ofmt"] = "xml"
#
#         xcmd = self.api.form_command(" ;".join(commands), formatting)
#         return await self.api.post(xcmd, formatting, strip_ns=strip_ns)
#
#     async def push_config(self, content: AnyStr):
#         xcmd = self.api.form_command(
#             cmd_input=" ; ".join(content.splitlines()),
#             formatting=dict(cmd_type="cli_conf", ofmt="xml"),
#         )
#         return await self.api.post_write_config(xcmd)
#
#     async def get_config(self, ofmt="text"):
#         res = await self.exec(["show running-config"], ofmt=ofmt, strip_ns=True)
#         return res[0].output
