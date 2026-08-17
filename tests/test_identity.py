from sportoto.identity import TeamIdentityResolver


def test_team_identity_resolver_normalizes_provider_aliases():
    resolver = TeamIdentityResolver({"Galatasaray": ["Galatasaray A.Ş.", "Galatasaray SK"], "Fenerbahce": ["Fenerbahçe A.Ş."]})
    assert resolver.resolve("Galatasaray A.Ş.") == "Galatasaray"
    assert resolver.resolve("fenerbahce") == "Fenerbahce"
    assert resolver.resolve("Unknown FC") == "Unknown FC"
