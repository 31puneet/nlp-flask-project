import json
import re
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from app.schema import SCHEMA_REGISTRY, SCHEMA_SUMMARY
from app.domain import resolve_domain_terms

PARAM_BLOCKLIST = {"sample_sets", "nobs_mode", "ci_method", "chunks", "inline_array", "drop_invariant", "variant_query", "site_mask", "min_cohort_size"}
PLOT_PARAM_ALLOWLIST = {"height", "width", "title"}

SYSTEM_PROMPT = f"""You are MalariaGEN Assistant, an expert in malaria genomics data analysis.
You translate natural language queries into exact API parameters mapping to the malariagen_data Python package.

AVAILABLE DATASETS:
- Ag3: Anopheles gambiae complex (includes gambiae, coluzzii, arabiensis)
- Af1: Anopheles funestus
- Pf8: Plasmodium falciparum
- Pv4: Plasmodium vivax

CRITICAL RULES:
1. Respond ONLY with a raw JSON object string. No markdown formatting, no code blocks, no explanation text.
2. The "parameters" dictionary must ONLY contain keys that exist in the method signature. Common valid keys are: transcript, sample_query, area_by, period_by, region, contig.
3. Format sample_query values as pandas query strings: "country == 'Kenya'" or "taxon == 'gambiae' and country in ['Kenya', 'Tanzania']".
4. Do NOT write Python code. Supply only dataset, method, parameters, and optional plot configuration.
5. If the method is 'aa_allele_frequencies_advanced', set plot_method to 'plot_frequencies_time_series'. Do NOT use 'plot_frequencies_heatmap'.
6. NEVER include these parameters: sample_sets, nobs_mode, ci_method, chunks, inline_array, drop_invariant, min_cohort_size, site_mask, variant_query.
7. For plot_parameters, ONLY include height, width, and title. No other keys.
8. If the user asks for sample metadata, use method 'sample_metadata'. If they ask for SNP data, use 'snp_allele_frequencies'. If they ask for amino acid frequencies, use 'aa_allele_frequencies_advanced'.
9. Always include area_by and period_by for frequency methods. Default area_by to 'country' and period_by to 'year' if not specified.
10. The transcript parameter must be a valid AgamP4 transcript ID in the format AGAPXXXXXX-RA.
11. When the user refers to previous results (e.g., "now filter that", "show those on a map"), use the conversation history to understand what they are referring to.

EXAMPLE JSON OUTPUT FORMAT:
{{
  "dataset": "Ag3",
  "method": "aa_allele_frequencies_advanced",
  "parameters": {{
    "transcript": "AGAP004707-RA",
    "area_by": "country",
    "period_by": "year",
    "sample_query": "taxon == 'gambiae' and country in ['Kenya', 'Tanzania']"
  }},
  "explanation": "KDR allele frequencies for gambiae in East Africa",
  "plot_method": "plot_frequencies_time_series",
  "plot_parameters": {{"title": "KDR frequencies in East Africa", "height": 600, "width": 800}}
}}

SECOND EXAMPLE (sample metadata):
{{
  "dataset": "Ag3",
  "method": "sample_metadata",
  "parameters": {{
    "sample_query": "country == 'Kenya'"
  }},
  "explanation": "Sample metadata for all samples collected in Kenya",
  "plot_method": null,
  "plot_parameters": null
}}

VALID METHODS AND THEIR EXACT PARAMETERS:
{SCHEMA_SUMMARY}
"""


class APIRequest(BaseModel):
    dataset: str
    method: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[str] = None
    plot_method: Optional[str] = None
    plot_parameters: Optional[Dict[str, Any]] = None


def _fix_sample_query(params):
    if "sample_query" in params:
        sq = params["sample_query"]
        sq = sq.replace('"', "'")
        sq = sq.replace("Cote d'Ivoire", "Cote d\\'Ivoire")
        params["sample_query"] = sq
    return params


def _validate(parsed_data: dict) -> dict:
    method = parsed_data.get("method")
    params = parsed_data.get("parameters", {})

    allowed = {}
    for entry in SCHEMA_REGISTRY.values():
        if entry["method"] == method:
            allowed.update(entry["parameters"])
            break

    cleaned_params = {}
    for param_name, param_value in params.items():
        if param_name in PARAM_BLOCKLIST:
            continue
        if param_name in allowed:
            cleaned_params[param_name] = param_value

    parsed_data["parameters"] = _fix_sample_query(cleaned_params)

    if parsed_data.get("plot_parameters"):
        parsed_data["plot_parameters"] = {
            k: v for k, v in parsed_data["plot_parameters"].items()
            if k in PLOT_PARAM_ALLOWLIST
        }

    return parsed_data


class NLPEngine:
    def __init__(self, api_key, model="gemini-2.5-flash"):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = model
        self.conversations: Dict[str, List[dict]] = {}

    def _get_history(self, session_id: str) -> List[dict]:
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]

    def process_query(self, user_query, session_id="default"):
        context = resolve_domain_terms(user_query.lower())
        enriched_query = user_query
        if context:
            enriched_query += "\n\nCRITICAL CONTEXT (use these exact values):\n" + json.dumps(context, indent=2)

        history = self._get_history(session_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-6:])
        messages.append({"role": "user", "content": enriched_query})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0
        )

        raw_output = response.choices[0].message.content
        cleaned_output = raw_output.replace("```json", "").replace("```", "").strip()
        cleaned_output = cleaned_output.replace("\\'", "'")

        try:
            parsed = json.loads(cleaned_output)
        except json.JSONDecodeError:
            cleaned_output = re.sub(r'\\(?!["\\/bfnrtu])', '', cleaned_output)
            parsed = json.loads(cleaned_output)

        validated = APIRequest(**parsed).model_dump()
        result = _validate(validated)

        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": json.dumps(result)})

        if len(history) > 20:
            self.conversations[session_id] = history[-20:]

        return result

    def clear_history(self, session_id="default"):
        self.conversations.pop(session_id, None)
