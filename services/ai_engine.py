"""
Claude AI integration — generates rich proposal justifications and refined recommendations.
"""
import os
import json
from typing import Optional


def generate_proposal_narrative(
    project: dict,
    proposals: list[dict],
    raw_text: str = "",
) -> list[dict]:
    """
    Enriches each proposal with an AI-generated justification narrative.
    Falls back gracefully if no API key is configured.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        return _add_fallback_narratives(proposals, project)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """You are a professional lighting design consultant.
Your role is to write compelling, technical, and persuasive proposal justifications
for lighting projects. Be concise (3-5 sentences per proposal), professional, and
highlight how each proposal matches the client's needs.
Always mention color temperature, lumen output, CRI, and energy efficiency.
Write in the same language the project description is in (Spanish or English)."""

        # Build a summary of each proposal
        proposals_summary = []
        for p in proposals:
            lamps_summary = []
            for r in p.get("room_assignments", []):
                lamps_summary.append(
                    f"  - {r['room']}: {r['quantity']}x {r['lamp_brand']} {r['lamp_model']} "
                    f"({r.get('lamp_color_temp','?')}, {r.get('lamp_lumens','?')}lm, "
                    f"CRI {r.get('lamp_cri','?')}, {'dimmable' if r.get('lamp_dimmable') else 'non-dimmable'}) "
                    f"= ${r.get('subtotal', 0):.0f}"
                )
            proposals_summary.append(
                f"Proposal {p['proposal_number']} — {p['title']} (${p['total_price']:.0f} total):\n"
                + "\n".join(lamps_summary)
            )

        user_message = f"""Project details:
- Type: {project.get('property_type', 'residential')}
- Level: {project.get('property_level', 'mid')}
- Size: {project.get('total_sqm', '?')} m²
- Rooms: {', '.join(project.get('rooms', []))}
- Style: {project.get('style', 'not specified')}
- Budget: ${project.get('budget_usd', 'not specified')}
- Special requirements: {project.get('special_requirements', 'none')}
{f'- Extracted from project file: {raw_text[:500]}' if raw_text else ''}

Proposals to justify:
{chr(10).join(proposals_summary)}

For each proposal, write a 3-5 sentence justification that:
1. Explains why this lighting selection fits the project
2. Highlights key technical advantages (color temp, CRI, lumens, efficiency)
3. Positions it relative to the other proposals (value vs premium)

Return a JSON array with objects: {{"proposal_number": 1, "justification": "..."}}"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
        )

        content = message.content[0].text.strip()
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        justifications = json.loads(content)
        just_map = {j["proposal_number"]: j["justification"] for j in justifications}

        for p in proposals:
            p["ai_justification"] = just_map.get(p["proposal_number"], "")

        return proposals

    except Exception as e:
        print(f"AI engine error: {e}")
        return _add_fallback_narratives(proposals, project)


def _add_fallback_narratives(proposals: list[dict], project: dict) -> list[dict]:
    """Generate basic narratives without AI."""
    level = project.get("property_level", "mid")
    sqm = project.get("total_sqm", "?")

    labels = {
        1: f"This Essential proposal provides efficient, cost-effective lighting for your {sqm}m² {level} project. Selected fixtures balance lumen output and energy consumption to meet standard illuminance targets.",
        2: f"This Comfort proposal upgrades your {sqm}m² project with improved CRI and colour temperature accuracy. Dimmable options are included for adaptable ambiance.",
        3: f"This Premium proposal delivers superior lighting quality with high-CRI fixtures and tunable colour temperatures, ideal for a {level} finish that impresses clients and enhances perceived value.",
    }
    for p in proposals:
        p["ai_justification"] = labels.get(p["proposal_number"], "")
    return proposals
