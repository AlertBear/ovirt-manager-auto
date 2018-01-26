"""
Helpers for documentation links tests.
"""

import requests
from lxml import html
from urlparse import urljoin

import config


class Link(object):
    """
    HTML <a> link entity.
    """
    def __init__(self, element=None):
        self._element = element

    @property
    def href(self):
        """
        Link 'href' property.

        Returns:
            (str) link 'href' attribute value
        """
        return self._element.attrib['href']

    @property
    def text(self):
        """
        Link text property.

        Returns:
            (str) link text
        """
        return self._element.text

    @property
    def is_reachable(self):
        """
        Property for link target reachability.

        Returns:
            (bool) whether link target is reachable (HTTP 200)
        """
        url = urljoin(config.root_url, self.href)
        with requests.get(url, verify=False, stream=True) as resp:
            return resp.ok


class WelcomePage(object):
    """
    Simple HTML web crawler for the welcome page.
    """
    def __init__(self):
        requests.packages.urllib3.disable_warnings()
        page = requests.get(config.root_url, verify=False)
        self._tree = html.fromstring(page.content)

    def get_link_by_id(self, link_id):
        """

        Args:
            link_id (str): ID attribute of the <a> link

        Returns:
            (Link) link entity, if link exists / (None) if link not found
        """
        try:
            return Link(
                self._tree.xpath('//a[@id="{0}"]'.format(link_id)).pop()
            )
        except IndexError:
            return None
