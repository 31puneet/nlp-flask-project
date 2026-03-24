import malariagen_data
import pandas as pd

GENE_MAPPING = {
    "kdr": {"transcript": "AGAP004707-RA", "gene_id": "AGAP004707", "description": "Vgsc, knockdown resistance"},
    "vgsc": {"transcript": "AGAP004707-RA", "gene_id": "AGAP004707", "description": "Voltage-gated sodium channel"},
    "ace1": {"transcript": "AGAP001356-RA", "gene_id": "AGAP001356", "description": "Acetylcholinesterase"},
    "rdl": {"transcript": "AGAP006028-RA", "gene_id": "AGAP006028", "description": "GABA receptor"},
    "gste2": {"transcript": "AGAP009194-RA", "gene_id": "AGAP009194", "description": "Glutathione S-transferase epsilon 2"},
    "cyp6aa1": {"transcript": "AGAP002862-RA", "gene_id": "AGAP002862", "description": "Cytochrome P450 6AA1"},
    "cyp6p3": {"transcript": "AGAP002865-RA", "gene_id": "AGAP002865", "description": "Cytochrome P450 6P3"},
    "cyp6p4": {"transcript": "AGAP002867-RA", "gene_id": "AGAP002867", "description": "Cytochrome P450 6P4"},
    "cyp6p1": {"transcript": "AGAP002868-RA", "gene_id": "AGAP002868", "description": "Cytochrome P450 6P1"},
    "cyp9k1": {"transcript": "AGAP000818-RA", "gene_id": "AGAP000818", "description": "Cytochrome P450 9K1"},
    "cyp6m2": {"transcript": "AGAP008212-RA", "gene_id": "AGAP008212", "description": "Cytochrome P450 6M2"},
    "cyp6z1": {"transcript": "AGAP008219-RA", "gene_id": "AGAP008219", "description": "Cytochrome P450 6Z1"},
    "tep1": {"transcript": "AGAP010815-RA", "gene_id": "AGAP010815", "description": "Thioester-containing protein 1"},
    "lrim1": {"transcript": "AGAP006348-RA", "gene_id": "AGAP006348", "description": "Leucine-rich immune protein 1"},
    "apl1": {"transcript": "AGAP007033-RA", "gene_id": "AGAP007033", "description": "Anopheles Plasmodium-responsive leucine-rich repeat 1"},
}

REGION_MAPPING = {
    "west africa": ["Benin", "Burkina Faso", "Cameroon", "Cote d'Ivoire", "Gambia, The", "Ghana", "Guinea", "Guinea-Bissau", "Mali", "Mauritania", "Niger", "Nigeria", "Senegal", "Sierra Leone", "Togo"],
    "east africa": ["Comoros", "Djibouti", "Eritrea", "Ethiopia", "Kenya", "Madagascar", "Malawi", "Mauritius", "Mozambique", "Rwanda", "Somalia", "South Sudan", "Tanzania", "Uganda"],
    "central africa": ["Cameroon", "Central African Republic", "Chad", "Democratic Republic of the Congo", "Equatorial Guinea", "Gabon", "Republic of the Congo"],
    "southern africa": ["Angola", "Botswana", "Eswatini", "Lesotho", "Malawi", "Mozambique", "Namibia", "South Africa", "Zambia", "Zimbabwe"],
    "sahel": ["Burkina Faso", "Chad", "Mali", "Mauritania", "Niger", "Nigeria", "Senegal"],
    "horn of africa": ["Djibouti", "Eritrea", "Ethiopia", "Somalia"],
    "great lakes": ["Burundi", "Democratic Republic of the Congo", "Kenya", "Rwanda", "Tanzania", "Uganda"],
}

COUNTRY_ALIASES = {
    "ivory coast": "Cote d'Ivoire",
    "cote divoire": "Cote d'Ivoire",
    "drc": "Democratic Republic of the Congo",
    "congo": "Republic of the Congo",
    "the gambia": "Gambia, The",
    "gambia": "Gambia, The",
    "car": "Central African Republic",
    "south sudan": "South Sudan",
}

SPECIES_MAPPING = {
    "gambiae": {"taxon": "gambiae", "dataset": "Ag3", "full_name": "Anopheles gambiae"},
    "coluzzii": {"taxon": "coluzzii", "dataset": "Ag3", "full_name": "Anopheles coluzzii"},
    "arabiensis": {"taxon": "arabiensis", "dataset": "Ag3", "full_name": "Anopheles arabiensis"},
    "funestus": {"taxon": "funestus", "dataset": "Af1", "full_name": "Anopheles funestus"},
    "falciparum": {"taxon": "falciparum", "dataset": "Pf8", "full_name": "Plasmodium falciparum"},
    "vivax": {"taxon": "vivax", "dataset": "Pv4", "full_name": "Plasmodium vivax"},
    "anopheles": {"taxon": None, "dataset": "Ag3", "full_name": "Anopheles (general)"},
    "mosquito": {"taxon": None, "dataset": "Ag3", "full_name": "Mosquito (general)"},
    "malaria": {"taxon": None, "dataset": "Ag3", "full_name": "Malaria vector (general)"},
}

CONTIG_MAPPING = {
    "chromosome 2l": "2L", "chromosome 2r": "2R", "chromosome 3l": "3L", "chromosome 3r": "3R", "chromosome x": "X",
    "chr2l": "2L", "chr2r": "2R", "chr3l": "3L", "chr3r": "3R", "chrx": "X",
    "2l": "2L", "2r": "2R", "3l": "3L", "3r": "3R",
}

_genome_cache = {}

def _load_genome_features(dataset_name="Ag3"):
    if dataset_name in _genome_cache:
        return _genome_cache[dataset_name]
    try:
        data = getattr(malariagen_data, dataset_name)()
        gf = data.genome_features()
        genes = gf[gf["type"] == "gene"][["ID", "Name", "description"]].copy()
        genes["Name_lower"] = genes["Name"].fillna("").str.lower()
        genes["ID_lower"] = genes["ID"].fillna("").str.lower()
        _genome_cache[dataset_name] = genes
        return genes
    except Exception:
        return None

def lookup_gene_dynamic(gene_query, dataset_name="Ag3"):
    gene_query_lower = gene_query.lower().strip()

    if gene_query_lower in GENE_MAPPING:
        return GENE_MAPPING[gene_query_lower]

    genes_df = _load_genome_features(dataset_name)
    if genes_df is None:
        return None

    name_match = genes_df[genes_df["Name_lower"] == gene_query_lower]
    if not name_match.empty:
        gene_id = name_match.iloc[0]["ID"]
        return {"transcript": f"{gene_id}-RA", "gene_id": gene_id, "description": str(name_match.iloc[0].get("description", ""))}

    id_match = genes_df[genes_df["ID_lower"] == gene_query_lower]
    if not id_match.empty:
        gene_id = id_match.iloc[0]["ID"]
        return {"transcript": f"{gene_id}-RA", "gene_id": gene_id, "description": str(id_match.iloc[0].get("description", ""))}

    partial_matches = genes_df[genes_df["Name_lower"].str.contains(gene_query_lower, na=False)]
    if not partial_matches.empty:
        gene_id = partial_matches.iloc[0]["ID"]
        return {"transcript": f"{gene_id}-RA", "gene_id": gene_id, "description": str(partial_matches.iloc[0].get("description", ""))}

    return None

def resolve_domain_terms(query_lower):
    resolved = {}

    found_gene = False
    for gene_name, gene_info in GENE_MAPPING.items():
        if gene_name in query_lower:
            resolved["gene"] = gene_name
            resolved["transcript"] = gene_info["transcript"]
            found_gene = True
            break

    if not found_gene:
        words = query_lower.replace(",", " ").split()
        for word in words:
            if len(word) >= 3 and word not in ("the", "and", "for", "from", "show", "get", "find", "plot", "allele", "frequency", "frequencies", "mutation", "mutations", "data", "sample", "samples"):
                result = lookup_gene_dynamic(word)
                if result:
                    resolved["gene"] = word
                    resolved["transcript"] = result["transcript"]
                    break

    for region_name, countries in REGION_MAPPING.items():
        if region_name in query_lower:
            resolved["region_group"] = region_name
            resolved["countries"] = countries
            break

    for alias, canonical in COUNTRY_ALIASES.items():
        if alias in query_lower:
            resolved["country"] = canonical
            break

    for species_name, species_info in SPECIES_MAPPING.items():
        if species_name in query_lower:
            resolved["species"] = species_info["taxon"]
            resolved["recommended_dataset"] = species_info["dataset"]
            break

    for contig_name, contig_val in CONTIG_MAPPING.items():
        if contig_name in query_lower:
            resolved["contig"] = contig_val
            break

    return resolved
