from lxml import etree

_xparser = etree.XMLParser(recover=True)


def strip_ns(root: etree.Element) -> etree.Element:
    """
    This function removes all namespace information from an XML Element tree
    so that a Caller can then use the `xpath` function without having
    to deal with the complexities of namespaces.
    """

    # first we visit each node in the tree and set the tag name to its localname
    # value; thus removing its namespace prefix

    for elem in root.getiterator():
        elem.tag = etree.QName(elem).localname

    # at this point there are no tags with namespaces, so we run the cleanup
    # process to remove the namespace definitions from within the tree.

    etree.cleanup_namespaces(root)
    return root


def fromstring(content):
    return etree.fromstring(content, parser=_xparser)


def tostring(ele):
    return etree.tostring(ele, pretty_print=True).decode()
