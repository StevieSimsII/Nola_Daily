from __future__ import annotations

import unittest

from noladaily.fetchers import _clean_headline, _clean_summary


class HeadlineCleaningTests(unittest.TestCase):
    def test_strips_domain_suffix(self) -> None:
        self.assertEqual(
            _clean_headline(
                "AG Murrill's attorney says another lawsuit possible over New Orleans public records - fox8live.com",
                "NOLA.com",
            ),
            "AG Murrill's attorney says another lawsuit possible over New Orleans public records",
        )

    def test_strips_matching_source(self) -> None:
        self.assertEqual(
            _clean_headline("Chef news around town - NOLA.com", "NOLA.com"),
            "Chef news around town",
        )

    def test_keeps_embedded_dashes(self) -> None:
        self.assertEqual(
            _clean_headline("Saints-Falcons preview from the Dome", "WWL"),
            "Saints-Falcons preview from the Dome",
        )

    def test_drops_title_plus_source_summary(self) -> None:
        self.assertEqual(
            _clean_summary(
                "New Orleans City Planning can't agree on data center regulations",
                "Axios",
                "New Orleans City Planning can't agree on data center regulations Axios",
                "City News",
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
