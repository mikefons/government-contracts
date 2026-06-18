"""Seed a realistic (synthetic) US-federal funding graph for the engine to reason over.

Shape mirrors what the USAspending / IT Dashboard / CBJ ingest would produce, so the
scoring and queries are demonstrable offline. Replace with real ingest in production.
"""
from datetime import date


def seed_federal(g) -> None:
    agencies = [
        ("dod", "Department of Defense", "DoD"),
        ("dhs", "Department of Homeland Security", "DHS"),
        ("va", "Department of Veterans Affairs", "VA"),
        ("treasury", "Department of the Treasury", "TREAS"),
        ("hhs", "Department of Health and Human Services", "HHS"),
    ]
    for k, name, abbr in agencies:
        g.add_vertex("agency", k, name=name, abbr=abbr)

    missions = [
        ("readiness", "Force readiness & logistics", 5),
        ("border", "Border & identity intelligence", 4),
        ("vet_care", "Veteran care modernization", 4),
        ("fin_crime", "Financial crime & sanctions", 5),
        ("pop_health", "Population health analytics", 3),
    ]
    for k, name, pr in missions:
        g.add_vertex("mission", k, name=name, priority=pr)

    techs = ["graph database", "knowledge graph", "entity resolution", "data fabric",
             "rag", "link analysis", "supply chain analytics", "ontology",
             "data lake", "ml platform", "case management", "identity"]
    for t in techs:
        g.add_vertex("technology", t.replace(" ", "_"), name=t)

    # program: (key, agency, mission, peo, dme_$, dme_growth, modernization, hiring_growth, techs, incumbent, contract_value, expiry)
    programs = [
        ("jadc2_data", "dod", "readiness", "PEO C3T", 42_000_000, 0.31, 0.86, 0.22,
         ["graph database", "data fabric", "supply chain analytics", "link analysis"], None, 0, None),
        ("logistics_twin", "dod", "readiness", "DLA J6", 18_500_000, 0.27, 0.74, 0.15,
         ["knowledge graph", "supply chain analytics", "ml platform"], "Palantir", 16_000_000, date(2027, 3, 31)),
        ("border_fusion", "dhs", "border", "CBP OIT", 28_000_000, 0.19, 0.81, 0.18,
         ["entity resolution", "link analysis", "identity", "data lake"], "LeidosX", 24_000_000, date(2026, 11, 30)),
        ("traveler_id", "dhs", "border", "TSA IT", 9_200_000, 0.08, 0.55, 0.05,
         ["identity", "ml platform"], "Accenture Federal", 11_000_000, date(2028, 6, 30)),
        ("vet_records", "va", "vet_care", "OIT DigitalHealth", 33_000_000, 0.24, 0.79, 0.12,
         ["knowledge graph", "data fabric", "case management", "rag"], None, 0, None),
        ("claims_ai", "va", "vet_care", "VBA Modernization", 14_000_000, 0.16, 0.68, 0.09,
         ["rag", "ml platform", "case management"], "Booz Allen", 13_500_000, date(2027, 1, 15)),
        ("sanctions_graph", "treasury", "fin_crime", "OFAC TechOffice", 21_500_000, 0.29, 0.83, 0.2,
         ["graph database", "entity resolution", "link analysis", "ontology"], None, 0, None),
        ("aml_platform", "treasury", "fin_crime", "FinCEN Tech", 12_800_000, 0.13, 0.6, 0.07,
         ["ml platform", "data lake"], "SAS", 12_000_000, date(2026, 9, 30)),
        ("pop_health_lake", "hhs", "pop_health", "CMS Data", 8_400_000, 0.06, 0.5, 0.04,
         ["data lake", "ml platform"], "Databricks", 9_000_000, date(2029, 2, 28)),
        (" resd_graph".strip(), "hhs", "pop_health", "NIH ODSS", 6_900_000, 0.22, 0.71, 0.11,
         ["knowledge graph", "ontology", "rag"], None, 0, None),
    ]
    for (k, ag, mis, peo, dme, growth, mod, hiring, ptech, incumbent, cval, expiry) in programs:
        g.add_vertex("program", k, name=k.replace("_", " ").title(), agency=ag, peo=peo)
        g.add_edge("owns", f"agency/{ag}", f"program/{k}")
        g.add_edge("influences", f"mission/{mis}", f"program/{k}")
        inv_key = f"inv_{k}"
        g.add_vertex("investment", inv_key, program=k, dme_amount=dme, dme_growth=growth,
                     modernization=mod, hiring_growth=hiring, fiscal_year=2026)
        g.add_edge("funds", f"investment/{inv_key}", f"program/{k}")
        for t in ptech:
            g.add_edge("uses", f"program/{k}", f"technology/{t.replace(' ', '_')}")
        if incumbent:
            vk = incumbent.lower().replace(" ", "_")
            if not g.vertex("vendor", vk):
                g.add_vertex("vendor", vk, name=incumbent)
            ck = f"ct_{k}"
            g.add_vertex("contract", ck, program=k, vendor=vk, value=cval,
                         expires=expiry.isoformat() if expiry else None)
            g.add_edge("supports", f"vendor/{vk}", f"program/{k}")
