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
    Throws:
        AssertionError: documentation link not found
    """
    requests.packages.urllib3.disable_warnings()
    testflow.step("Fetching welcome page %s", config.root_url)
    page = requests.get(config.root_url, verify=False)
    tree = html.fromstring(page.content)
    for resource in config.WEB_IDS.values():
        for link_id in resource:
            href_tail = tree.xpath("//a[@id='{0}']/@href".format(link_id))
            if not href_tail:
                raise AssertionError(
                    "Documentation link for %s (%s) is missing"
                    % (resource, link_id)
                )
            link = "{0}/{1}".format(config.root_url, href_tail[0])
            yield link


def check_link(link):
    """
    Description:
        Checks if GET HTTP request for a given link responded with
        HTTP 200-ish code.
    Args:
        link (str): Link for check.
    Returns:
        tuple(bool, str): If status code is ok.
    """
    requests.packages.urllib3.disable_warnings()

    testflow.step("Checking %s.", link)
    resp = requests.get(link, verify=False)
    return resp.ok


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
