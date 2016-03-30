from uritemplate import expand, variables


class URITemplate(object):
    def __init__(self, uri_template):
        self.uri_template = uri_template

    def variables(self):
        return variables(self.uri_template)

    def sub(self, values):
        return expand(self.uri_template, values)


if __name__ == "__main__":
    import unittest

    class TestURITemplate(unittest.TestCase):
        def test_simple(self):
            t = URITemplate("http://example.org/news/{id}/")
            self.assertEqual(set(["id"]), t.variables())
            self.assertEqual(
                "http://example.org/news/joe/", t.sub({"id": "joe"})
            )

            t = URITemplate(
                "http://www.google.com/notebook/feeds/{userID}"
                "{-prefix|/notebooks/|notebookID}{-opt|/-/|categories}"
                "{-list|/|categories}?"
                "{-join|&|updated-min,updated-max,alt,start-index,max-results,"
                "entryID,orderby}"
            )
            self.assertEqual(
                "http://www.google.com/notebook/feeds/joe?",
                t.sub({"userID": "joe"})
            )

    unittest.main()
