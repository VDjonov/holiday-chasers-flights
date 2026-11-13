"""Share pages stay on the deal they were created for. Run: python social/test_share_pages.py"""
import json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_posts as g


def deal(ap, code, price, dep, ret, city="X"):
    return dict(ap=ap, kind="week", code=code, city=city, price=price, dep=dep, ret=ret, stops=0, airline="")


def main():
    assert g.PINNED_SHARES == frozenset({"hero_dub_classic", "sun_dub_classic", "sun_ork_classic"})

    porto = [deal("DUB", "OPO", 39, "2026-12-05", "2026-12-12", "Porto")]
    faro = [deal("DUB", "FAO", 38, "2026-12-12", "2026-12-19", "Faro")]
    assert g.share_id("classic", porto, "hero_dub") == "dub-opo-20261205-20261212-39-classic"
    assert g.share_id("classic", porto, "hero_dub") != g.share_id("classic", faro, "hero_dub")
    # A higher price is a different page, so the old link keeps the price that was posted.
    dearer = [deal("DUB", "OPO", 40, "2026-12-05", "2026-12-12", "Porto")]
    assert g.share_id("classic", porto, "hero_dub") != g.share_id("classic", dearer, "hero_dub")
    # The slot name is not part of a deal id: the same fare always maps to the same page.
    assert g.share_id("classic", porto, "hero_dub") == g.share_id("classic", porto, "sun_dub")
    assert g.share_id("classic", porto, "hero_dub") not in g.PINNED_SHARES
    assert g.share_id("ivory", [], "trip_glance") == "trip_glance_ivory"
    # A new share lands on the scanned dates. The page id does not change.
    assert g.link(porto[0]) == (
        "holidaychasers.ie/?dest=OPO&from=DUB&out=2026-12-05&ret=2026-12-12"
        "&utm_source=facebook&utm_medium=social"
    )
    assert g.share_id("classic", porto, "hero_dub") == "dub-opo-20261205-20261212-39-classic"
    undated = dict(porto[0], dep="", ret="")
    assert "out=" not in g.link(undated) and "ret=" not in g.link(undated)
    assert "dest=OPO" in g.link(undated) and "from=DUB" in g.link(undated)

    sun = [
        deal("DUB", "AGP", 40, "2027-01-09", "2027-01-16", "Malaga"),
        deal("DUB", "FAO", 45, "2026-12-05", "2026-12-12", "Faro"),
    ]
    assert g.share_id("classic", sun, "sun_dub") == (
        "dub-agp-20270109-20270116-40-dub-fao-20261205-20261212-45-classic"
    )

    with tempfile.TemporaryDirectory() as d:
        for sid in g.PINNED_SHARES:
            assert g.share_is_frozen(sid, d)
        g.publish_share_pages([
            ("hero_dub_classic", "WRONG", "d", "https://example/card.jpg", "https://example/?dest=FAO"),
            ("dub-opo-20261205-20261212-39-classic", "Dublin to Porto from €39 return per person", "d",
             "https://holidaychasers.ie/social/card/dub-opo-20261205-20261212-39-classic.jpg",
             "https://holidaychasers.ie/?dest=OPO&from=DUB&utm_source=facebook&utm_medium=social"),
        ], d)
        assert not os.path.exists(os.path.join(d, "hero_dub_classic.html"))
        path = os.path.join(d, "dub-opo-20261205-20261212-39-classic.html")
        first = open(path, encoding="utf-8").read()
        assert "Porto" in first and "€39" in first and "dest=OPO" in first
        assert "Faro" not in first and "dest=FAO" not in first
        # A later run with a different fare must not rewrite the existing page.
        g.publish_share_pages([
            ("dub-opo-20261205-20261212-39-classic", "Dublin to Faro from €38 return per person", "d",
             "https://holidaychasers.ie/social/card/other.jpg",
             "https://holidaychasers.ie/?dest=FAO&from=DUB&utm_source=facebook&utm_medium=social"),
        ], d)
        assert open(path, encoding="utf-8").read() == first
        g.publish_share_pages([
            ("dub-fao-20261212-20261219-38-classic", "Dublin to Faro from €38 return per person", "d",
             "https://holidaychasers.ie/social/card/dub-fao-20261212-20261219-38-classic.jpg",
             "https://holidaychasers.ie/?dest=FAO&from=DUB&utm_source=facebook&utm_medium=social"),
        ], d)
        assert os.path.exists(os.path.join(d, "dub-fao-20261212-20261219-38-classic.html"))
        assert open(path, encoding="utf-8").read() == first
        dated_id = "dub-opo-20261205-20261212-46-classic"
        dated_url = "https://" + g.link(deal("DUB", "OPO", 46, "2026-12-05", "2026-12-12", "Porto"))
        g.publish_share_pages([
            (dated_id, "Dublin to Porto from €46 return per person", "d",
             "https://holidaychasers.ie/social/card/" + dated_id + ".jpg", dated_url),
        ], d)
        dated_path = os.path.join(d, dated_id + ".html")
        dated_html = open(dated_path, encoding="utf-8").read()
        assert "out=2026-12-05" in dated_html and "ret=2026-12-12" in dated_html
        assert "from=DUB" in dated_html and "dest=OPO" in dated_html
        g.publish_share_pages([
            (dated_id, "CHANGED", "d", "https://example/other.jpg", "https://example/?dest=FAO"),
        ], d)
        assert open(dated_path, encoding="utf-8").read() == dated_html
        assert open(path, encoding="utf-8").read() == first

    print("ok")


if __name__ == "__main__":
    main()
