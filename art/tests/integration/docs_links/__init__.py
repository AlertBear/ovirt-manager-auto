from lxml import html
import requests

from art.unittest_lib import testflow

import config


def get_links():
    """
    Description:
        Makes a generator of links.
    Yields:
        str: Link to a documentation resource.
    """
    requests.packages.urllib3.disable_warnings()

    for resource in config.WEB_IDS.values():
        for id in resource:
            page = requests.get(config.root_url, verify=False)
            tree = html.fromstring(page.content)
            tail = tree.xpath("//a[@id='{0}']/@href".format(id))
            link = "{0}/{1}".format(config.root_url, tail[0])
            yield link


def check_link(link):
    """
    Description:
        Checks if GET HTTP request for a given link responded with
        HTTP 200.
    Args:
        link (str): Link for check.
    Returns:
        tuple(bool, str): If status code is ok.
    """
    requests.packages.urllib3.disable_warnings()

    testflow.step("Checking %s.", link)
    status_code = requests.get(link, verify=False).status_code
    return (status_code == config.HTTP_OK, link)


def check_links():
    """
    Description:
       Simple functor to run links check for a collection taken from
       get_links() function.
    Returns:
       tuple(bool, str): False and link if there are any not HTTP OK
       responded links, True and None otherwise.
    """
    def generate(links):
        for link in links:
            yield check_link(link)

    links = get_links()

    for result in generate(links):
        if not result[0]:
            return result
    return True, None
