import re
import json
from typing import Tuple

from bson import ObjectId
from fastapi import HTTPException
from openai import OpenAI
from anthropic import Anthropic

from app.core.config import get_settings
from app.db.mongo import get_spokes_collection
from app.schemas.spoke import SpokeCreateRequest, SpokeContent, SpokeInDB
from app.core.pdf import render_spoke_pdf

settings = get_settings()

openai_client = (
    OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
)
anthropic_client = (
    Anthropic(api_key=settings.anthropic_api_key)
    if settings.anthropic_api_key
    else None
)

def _ensure_oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

def _build_spoke_prompt(req: SpokeCreateRequest) -> str:
    return f"""
You are a MongoDB Sales Development coach.

Write a short, structured Spoke in PLAIN TEXT using the EXACT section labels below.
Do not use markdown, do not use backticks, do not output JSON.

Use this format, in this exact order, with a blank line between sections:

COMPANY:
...

SPOKE_NAME:
...

HYPOTHESIS_WHAT_THEY_DO:
...

HYPOTHESIS_WHY_MONGO_ONE_LINER:
...

HYPOTHESIS_BUSINESS_VALUE:
...

WHY_MONGODB_PAIN:
...

WHY_MONGODB_GAIN:
...

PROOF_POINTS:
- Customer A: ...
- Customer B: ...

TALK_TRACK:
...

EMAIL_SUBJECT:
...

EMAIL_BODY:
...

WHY_ANYTHING:
...

WHY_MONGODB:
...

WHY_NOW:
...

Content constraints:
- Simple, direct language an SDR would actually say/write.
- Each field should be short (1–3 sentences max; proof points 1 line each).
- Avoid fluffy phrases like "at scale", "world-class", "industry-leading".
- Do NOT invent specific $ amounts or metrics unless they appear in the input.

Context:

COMPANY: {req.company}

NOTES (highest priority context):
{req.notes or "(none)"}

TRANSCRIPT (second priority context):
{req.transcript or "(none)"}

EXTRA INSTRUCTIONS FROM REP:
{req.extra_instructions or "(none)"}
""".strip()

def _call_openai(req: SpokeCreateRequest, prompt: str) -> str:
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI not configured")
    resp = openai_client.chat.completions.create(
        model=req.model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": "You output STRICT JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content

def _call_anthropic(req: SpokeCreateRequest, prompt: str) -> str:
    if not anthropic_client:
        raise HTTPException(status_code=500, detail="Anthropic not configured")

    model_id = req.model or "claude-opus-4-6"

    resp = anthropic_client.messages.create(
        model=model_id,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    text_parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return "".join(text_parts)

def _extract_section(text: str, label: str) -> str:
    """
    Extract the text following 'LABEL:' up to the next ALL_CAPS_LABEL: or end of string.
    """
    pattern = rf"{label}:\s*(.*?)(?=\n[A-Z_]+:|\Z)"
    m = re.search(pattern, text, flags=re.S)
    if not m:
        return ""
    value = m.group(1).strip()
    return value

def generate_spoke_content(req: SpokeCreateRequest) -> SpokeContent:
    prompt = _build_spoke_prompt(req)

    if req.provider == "openai":
        raw = _call_openai(req, prompt)
    else:
        raw = _call_anthropic(req, prompt)

    raw = (raw or "").strip()

    # Parse sections from the plain-text response
    company = req.company.strip()

    spoke_name = _extract_section(raw, "SPOKE_NAME") or f"{company} – Spoke"
    hypothesis_what = _extract_section(raw, "HYPOTHESIS_WHAT_THEY_DO")
    hypothesis_why = _extract_section(raw, "HYPOTHESIS_WHY_MONGO_ONE_LINER")
    hypothesis_value = _extract_section(raw, "HYPOTHESIS_BUSINESS_VALUE")

    pain = _extract_section(raw, "WHY_MONGODB_PAIN")
    gain = _extract_section(raw, "WHY_MONGODB_GAIN")

    proof_block = _extract_section(raw, "PROOF_POINTS")
    proof_points = []
    for line in proof_block.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        # Expect format: "- Name: summary"
        line = line[1:].strip()
        if ":" in line:
            name, summary = line.split(":", 1)
            proof_points.append(
                {"name": name.strip(), "summary": summary.strip()}
            )

    talk_track = _extract_section(raw, "TALK_TRACK")

    email_subject = _extract_section(raw, "EMAIL_SUBJECT") or f"Exploring MongoDB with {company}"
    email_body = _extract_section(raw, "EMAIL_BODY")

    why_anything = _extract_section(raw, "WHY_ANYTHING")
    why_mongodb = _extract_section(raw, "WHY_MONGODB")
    why_now = _extract_section(raw, "WHY_NOW")

    # Build SpokeContent; fill gaps with safe defaults
    return SpokeContent(
        company=company,
        spoke_name=spoke_name,
        hypothesis={
            "what_they_do": hypothesis_what or f"{company} is building and running data-driven systems.",
            "why_mongo_one_liner": hypothesis_why or "MongoDB Atlas gives them a flexible, scalable operational data platform.",
            "business_value": hypothesis_value or "Faster delivery of new features, lower operational overhead, and more resilient apps.",
        },
        why_mongodb={
            "pain": pain or "Legacy / fragmented data stack slows down new initiatives and adds complexity.",
            "gain": gain or "MongoDB simplifies the operational data layer and supports new workloads without constant rework.",
        },
        proof_points=proof_points or [
            {
                "name": "Reference customer",
                "summary": "Uses MongoDB Atlas to simplify their data stack and ship new features faster.",
            }
        ],
        talk_track=talk_track or (
            f"I’ve been looking at how {company} is handling data-heavy workloads and new projects. "
            "A lot of teams in a similar spot are hitting limits with legacy databases or a mix of point solutions. "
            "I’d like to compare that to how other teams are using MongoDB Atlas as a central, flexible data layer."
        ),
        email_template={
            "subject": email_subject,
            "body": email_body
            or (
                f"Hi <First Name>,\n\n"
                f"I’ve been looking at how teams like {company} handle data-heavy workloads and new initiatives. "
                "We often see that legacy databases and stitched-together point solutions make it harder to move quickly without adding complexity.\n\n"
                "MongoDB Atlas is being used as a central, flexible data platform for both core applications and newer AI/analytics projects. "
                "That often simplifies the stack while giving engineering more room to ship.\n\n"
                "Would you be open to a short conversation to compare how you’re approaching this today with what we’re seeing work well elsewhere?\n\n"
                "Best,\n<Your Name>\nMongoDB"
            ),
        },
        three_whys={
            "why_anything": why_anything
            or "Staying on a rigid or fragmented data stack makes each new project slower and more fragile.",
            "why_mongodb": why_mongodb
            or "MongoDB Atlas provides a single, flexible operational data layer that matches how modern apps are built.",
            "why_now": why_now
            or "Most teams are being pushed to deliver more data-driven and AI-enabled features soon; having the right data platform in place reduces friction.",
        },
    )

async def create_spoke(req: SpokeCreateRequest) -> SpokeInDB:
    col = get_spokes_collection()
    content = generate_spoke_content(req)
    doc = content.model_dump()
    result = await col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return SpokeInDB(**doc)

async def get_spoke(spoke_id: str) -> SpokeInDB:
    col = get_spokes_collection()
    doc = await col.find_one({"_id": _ensure_oid(spoke_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Spoke not found")
    doc["_id"] = str(doc["_id"])
    return SpokeInDB(**doc)

async def get_spoke_pdf_bytes(spoke_id: str) -> Tuple[SpokeInDB, bytes]:
    spoke = await get_spoke(spoke_id)
    spoke_content = SpokeContent.model_validate(
        spoke.model_dump(exclude={"id"}, by_alias=False)
    )
    pdf = render_spoke_pdf(spoke_content)
    return spoke, pdf