import re
from lxml import etree

_xparser = etree.XMLParser(recover=True)


_REGEX_tags_with_ns = re.compile(r"</?((\S+?:)[^<]+)>", re.MULTILINE)


def _sub_ns_remove(mo):
    orig_tag = mo.string[mo.start() : mo.end()]
    ns = mo.group(2)
    new_tag = orig_tag.replace(ns, "")
    return new_tag


def strip_ns(content):
    return _REGEX_tags_with_ns.sub(repl=_sub_ns_remove, string=content)


def fromstring(content):
    return etree.fromstring(content, parser=_xparser)


def tostring(ele):
    return etree.tostring(ele, pretty_print=True).decode()
