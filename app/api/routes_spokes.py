from fastapi import APIRouter, Response

from app.core import pdf
from app.schemas import spoke
from app.schemas.spoke import SpokeCreateRequest, SpokeInDB
from app.services.spoke_generator import create_spoke, get_spoke, get_spoke_pdf_bytes

router = APIRouter(prefix="/spokes", tags=["spokes"])

@router.post("/generate", response_model=SpokeInDB)
async def generate_spoke(req: SpokeCreateRequest):
    return await create_spoke(req)

@router.get("/{spoke_id}", response_model=SpokeInDB)
async def read_spoke(spoke_id: str):
    return await get_spoke(spoke_id)

@router.get("/{spoke_id}/pdf")
async def read_spoke_pdf(spoke_id: str):
    spoke, pdf = await get_spoke_pdf_bytes(spoke_id)
    filename = f"{spoke.company.replace(' ', '_')}_spoke.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )