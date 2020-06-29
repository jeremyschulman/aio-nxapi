from typing import Optional, AnyStr, Tuple
from socket import getservbyname
import httpx
import base64
import ssl
from lxml import etree
from collections import namedtuple

__all__ = [
    'Device',
    'CommandResults'
]

_ssl_context = ssl.SSLContext(ssl_version=ssl.PROTOCOL_TLSv1_1)


_NXAPI_CMD_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<ins_api>
<version>{api_ver}</version>
<type>{cmd_type}</type>
<chunk>{chunk}</chunk>
<sid>{sid}</sid>
<input>{cmd_input}</input>
<output_format>{ofmt}</output_format>
</ins_api>"""

CommandResults = namedtuple("CommandResuls", ["ok", "command", "results"])


class Transport(object):
    CMDTYPES_OPTIONS = ("cli_show", "cli_show_ascii", "cli_conf", "bash")
    OFMT_OPTIONS = ("xml", "json", "text")

    def __init__(self, host, proto, port, creds):
        port = port or getservbyname(proto)
        self.client = httpx.AsyncClient(
            base_url=httpx.URL(f"{proto}://{host}:{port}"), verify=_ssl_context
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

    def form_command(self, cmd_input, cmd_type=None, ofmt=None, sid=None):
        return _NXAPI_CMD_TEMPLATE.format(
            api_ver="1.2",
            cmd_type=cmd_type or self.cmd_type,
            cmd_input=cmd_input,
            chunk=0,
            sid=sid or "sid",
            ofmt=ofmt or self.ofmt,
        )

    async def post(self, xcmd):
        res = await self.client.post("/ins", data=xcmd)
        res.raise_for_status()
        as_xml = etree.XML(res.text)

        return [
            CommandResults(
                ok=cmd_res.findtext("code") == "200",
                command=cmd_res.findtext("input").strip(),
                results=cmd_res.find("body"),
            )
            for cmd_res in as_xml.xpath("outputs/output")
        ]


class Device(object):
    def __init__(
        self,
        host: AnyStr,
        creds: Tuple[str, str],
        proto: Optional[AnyStr] = "https",
        port=None,
    ):
        self.api = Transport(host=host, creds=creds, proto=proto, port=port)

    async def exec(self, commands):
        """
        Execute a list of operational commands and return the output as a list of CommandResults.
        """
        return await self.api.post(self.api.form_command(' ;'.join(commands)))
