"""
This module provides the asyncio client for Cisco NX-API, expected to work on:
    * N3K system
    * N5K system  (tested)
    * N7K system
    * N9K system
"""

from typing import Optional, AnyStr, Tuple, List

import json
from socket import getservbyname
import httpx
import base64
import ssl
from collections import namedtuple

from . import xmlhelp


__all__ = ["Device", "CommandResults"]

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

CommandResults = namedtuple("CommandResults", ["ok", "command", "output"])


class Transport(object):
    CMDTYPES_OPTIONS = ("cli_show", "cli_show_ascii", "cli_conf", "bash")
    OFMT_OPTIONS = ("xml", "json", "text")
    API_VER = "1.0"

    def __init__(self, host, proto, port, creds, timeout=60):
        port = port or getservbyname(proto)

        self.client = httpx.AsyncClient(
            base_url=httpx.URL(f"{proto}://{host}:{port}"),
            verify=_ssl_context,
            timeout=httpx.Timeout(timeout),
        )

        self.client.headers["Content-Type"] = "application/xml"
        self.b64auth = (
            base64.encodebytes(bytes("%s:%s" % creds, encoding="utf-8"))
            .decode()
            .replace("\n", "")
        )
        self.client.headers["Authorization"] = "Basic %s" % self.b64auth

        self.username = creds[0]
        self.cmd_type = "cli_show"
        self.ofmt = "xml"

    @property
    def timeout(self):
        return self.client.timeout

    @timeout.setter
    def timeout(self, value):
        self.client.timeout = httpx.Timeout(value)

    def form_command(self, cmd_input, formatting, sid=None):
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

    async def post(self, xcmd, formatting, strip_ns=False):
        res = await self.client.post("/ins", data=xcmd)
        res.raise_for_status()

        if formatting["ofmt"] == "json":
            as_json = json.loads(res.text)

            outputs = as_json["ins_api"]["outputs"]["output"]
            if not isinstance(outputs, list):
                outputs = [outputs]

            return [
                CommandResults(
                    ok=cmd_res["code"] == "200",
                    command=cmd_res["input"],
                    output=cmd_res["body"],
                )
                for cmd_res in outputs
            ]

        # Output format is "xml" or "text"; but in either case the body content
        # is extracted in the same manner.

        as_text = xmlhelp.strip_ns(res.text) if strip_ns else res.text
        as_xml = xmlhelp.fromstring(as_text)

        def body_is_text(_res_e):
            return _res_e.find("body").text.strip()

        def body_is_xml(_res):
            return _res.find("body")

        get_output = (
            body_is_text if formatting["cmd_type"] == "cli_show_ascii" else body_is_xml
        )

        return [
            CommandResults(
                ok=cmd_res.findtext("code") == "200",
                command=cmd_res.findtext("input").strip(),
                output=get_output(cmd_res),
            )
            for cmd_res in as_xml.xpath("outputs/output")
        ]

    async def post_write_config(self, xcmd):
        """
        This coroutine is used to push the configuration to the device an return any
        error XML elements.  If no errors then return value is None.
        """
        res = await self.client.post("/ins", data=xcmd)
        res.raise_for_status()
        as_xml = xmlhelp.fromstring(res.text)

        if any_errs := as_xml.xpath(".//code[. != '200']"):
            return any_errs

        return None


class Device(object):
    def __init__(
        self,
        host: AnyStr,
        creds: Tuple[str, str],
        proto: Optional[AnyStr] = "https",
        port=None,
        private=None,
    ):
        self.api = Transport(host=host, creds=creds, proto=proto, port=port)
        self.private = private
        self.host = host

    async def exec(
        self, commands: List[AnyStr], ofmt: Optional[AnyStr] = None, strip_ns=False
    ) -> List[CommandResults]:
        """
        Execute a list of operational commands and return the output as a list of CommandResults.
        """
        formatting = dict(ofmt=ofmt)

        if ofmt == "text":
            formatting["cmd_type"] = "cli_show_ascii"
            formatting["ofmt"] = "xml"

        xcmd = self.api.form_command(" ;".join(commands), formatting)
        return await self.api.post(xcmd, formatting, strip_ns=strip_ns)

    async def push_config(self, content: AnyStr):
        xcmd = self.api.form_command(
            cmd_input=" ; ".join(content.splitlines()),
            formatting=dict(cmd_type="cli_conf", ofmt="xml"),
        )
        return await self.api.post_write_config(xcmd)

    async def get_config(self, ofmt="text"):
        res = await self.exec(["show running-config"], ofmt=ofmt, strip_ns=True)
        return res[0].output
