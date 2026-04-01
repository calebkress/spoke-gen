from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit  # NEW

from app.schemas.spoke import SpokeContent

def render_spoke_pdf(spoke: SpokeContent) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER

    x_margin = 0.75 * inch
    max_width = width - 2 * x_margin
    y = height - 0.75 * inch
    line_height = 14

    def draw_text(text: str = "", bold: bool = False):
        nonlocal y
        if text is None:
            text = ""
        text = text.strip()
        if text == "":
            # blank line
            y -= line_height
            return

        font_name = "Helvetica-Bold" if bold else "Helvetica"
        font_size = 11 if bold else 10
        c.setFont(font_name, font_size)

        # Wrap text to fit the available width
        lines = simpleSplit(text, font_name, font_size, max_width)
        for line in lines:
            if y < 1 * inch:
                c.showPage()
                y = height - 0.75 * inch
                c.setFont(font_name, font_size)
            c.drawString(x_margin, y, line)
            y -= line_height

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, f"Spoke – {spoke.company}")
    y -= 2 * line_height

    # SPOKE
    draw_text("SPOKE", bold=True)
    draw_text(spoke.spoke_name)
    y -= line_height

    # Hypothesis / Theory
    draw_text("Hypothesis / Theory", bold=True)
    draw_text(f"What they do: {spoke.hypothesis.get('what_they_do', '')}")
    draw_text(f"Why Mongo (one line): {spoke.hypothesis.get('why_mongo_one_liner', '')}")
    draw_text(f"Business value: {spoke.hypothesis.get('business_value', '')}")
    y -= line_height

    # Why MongoDB – Pain & Gain
    draw_text("Why MongoDB – Pain & Gain", bold=True)
    draw_text(f"Pain: {spoke.why_mongodb.get('pain', '')}")
    draw_text(f"Gain: {spoke.why_mongodb.get('gain', '')}")
    y -= line_height

    # Proof Points
    draw_text("Proof Points", bold=True)
    for p in spoke.proof_points:
        draw_text(f"- {p.name}: {p.summary}")
    y -= line_height

    # Talk Track
    draw_text("Talk Track", bold=True)
    draw_text(spoke.talk_track)
    y -= line_height

    if y < height - 2 * inch: 
        c.showPage()
        y = height - 0.75 * inch

    # Email Template
    draw_text("Email Template", bold=True)
    draw_text(f"Subject: {spoke.email_template.subject}")
    draw_text(spoke.email_template.body)
    y -= line_height

    # 3 Whys
    draw_text("3 Whys", bold=True)
    draw_text(f"Why Anything? {spoke.three_whys.why_anything}")
    draw_text(f"Why MongoDB? {spoke.three_whys.why_mongodb}")
    draw_text(f"Why Now? {spoke.three_whys.why_now}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()