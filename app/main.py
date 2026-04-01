from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.api.routes_spokes import router as api_spokes_router
from app.schemas.spoke import SpokeCreateRequest
from app.services.spoke_generator import create_spoke, get_spoke_pdf_bytes

app = FastAPI(title="Spoke Service")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_provider": "anthropic",
            "default_model_openai": "gpt-4.1-mini",
            "default_model_anthropic": "claude-3-5-sonnet-latest",
        },
    )

@app.post("/generate", response_class=Response)
async def generate_spoke_web(
    request: Request,
    company: str = Form(...),
    notes: str = Form(""),
    transcript: str = Form(""),
    provider: str = Form("openai"),
    model: str = Form("gpt-4.1-mini"),
    extra_instructions: str = Form(""),
):
    req_model = SpokeCreateRequest(
        company=company,
        notes=notes,
        transcript=transcript,
        provider=provider,
        model=model,
        extra_instructions=extra_instructions,
    )

    spoke = await create_spoke(req_model)
    _, pdf_bytes = await get_spoke_pdf_bytes(spoke.id)

    safe_company = company.replace(" ", "_")
    filename = f"{safe_company}_spoke.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

app.include_router(api_spokes_router, prefix="/api")