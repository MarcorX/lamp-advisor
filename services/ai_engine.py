"""
Proposal narrative generator — uses unified AI client.
"""
import json
from services.ai_client import get_client


def generate_proposal_narrative(project: dict, proposals: list[dict], raw_text: str = "") -> list[dict]:
    client = get_client()
    if not client.is_configured():
        return _add_fallback_narratives(proposals, project)

    try:
        system = (
            "You are a professional lighting design consultant. "
            "Write compelling, technical, and persuasive proposal justifications. "
            "Be concise (3-5 sentences), professional, and highlight how each proposal "
            "matches the client's needs. Always mention color temperature, lumen output, "
            "CRI, and energy efficiency. Write in the same language as the project description."
        )

        summaries = []
        for p in proposals:
            lamps = [
                f"  - {r['room']}: {r['quantity']}x {r['lamp_brand']} {r['lamp_model']} "
                f"({r.get('lamp_color_temp','?')}, {r.get('lamp_lumens','?')}lm, "
                f"CRI {r.get('lamp_cri','?')}, "
                f"{'dimmable' if r.get('lamp_dimmable') else 'non-dim'}) "
                f"= ${r.get('subtotal', 0):.0f}"
                for r in p.get("room_assignments", [])
            ]
            summaries.append(
                f"Proposal {p['proposal_number']} — {p['title']} "
                f"(${p['total_price']:.0f} total):\n" + "\n".join(lamps)
            )

        user_msg = (
            f"Project: {project.get('property_type')} / {project.get('property_level')} / "
            f"{project.get('total_sqm','?')}m² / rooms: {', '.join(project.get('rooms', []))}\n"
            f"Style: {project.get('style','?')} | Budget: ${project.get('budget_usd','?')}\n"
            f"{f'File extract: {raw_text[:400]}' if raw_text else ''}\n\n"
            + "\n\n".join(summaries)
            + "\n\nFor each proposal write a 3-5 sentence justification. "
            "Return JSON array: [{\"proposal_number\":1,\"justification\":\"...\"}]"
        )

        content = client.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=system,
            max_tokens=1500,
        )

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        just_map = {j["proposal_number"]: j["justification"] for j in json.loads(content)}
        for p in proposals:
            p["ai_justification"] = just_map.get(p["proposal_number"], "")
        return proposals

    except Exception as e:
        print(f"AI narrative error: {e}")
        return _add_fallback_narratives(proposals, project)


def _add_fallback_narratives(proposals, project):
    level = project.get("property_level", "mid")
    sqm = project.get("total_sqm", "?")
    labels = {
        1: f"This Essential proposal provides efficient, cost-effective lighting for your {sqm}m² {level} project.",
        2: f"This Comfort proposal upgrades your {sqm}m² project with improved CRI and dimmable options.",
        3: f"This Premium proposal delivers superior lighting quality ideal for a {level} finish.",
    }
    for p in proposals:
        p["ai_justification"] = labels.get(p["proposal_number"], "")
    return proposals
