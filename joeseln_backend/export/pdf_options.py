"""
shared export PDF layout settings
* margins
* page numbering
* header
"""

from datetime import datetime, timezone
from html import escape
from io import BytesIO

from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


class PdfOptions(BaseModel):
    margin_top: float = Field(20, ge=0, le=80)
    margin_right: float = Field(20, ge=0, le=80)
    margin_bottom: float = Field(20, ge=0, le=80)
    margin_left: float = Field(20, ge=0, le=80)
    page_numbers: bool = True
    header: str = Field("", max_length=300)

    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def render_options(self):
        top = max(self.margin_top, 15) if self.header else self.margin_top
        bottom = (
            max(self.margin_bottom, 15) if self.page_numbers else self.margin_bottom
        )
        return {
            "format": "A4",
            "margin": {
                "top": f"{top}mm",
                "right": f"{self.margin_right}mm",
                "bottom": f"{bottom}mm",
                "left": f"{self.margin_left}mm",
            },
            "display_header_footer": bool(self.header),
            "header_template": (
                '<div style="font: 9pt Helvetica, Arial, sans-serif; width: 100%; display: flex; '
                'align-items: baseline; gap: 12px; '
                f'margin: 0 {self.margin_right}mm 0 {self.margin_left}mm;">'
                '<strong style="flex: 1; min-width: 0; overflow: hidden; '
                'white-space: nowrap; text-overflow: ellipsis;">'
                f'{escape(self.header)}</strong>'
                '<span style="flex-shrink: 0;">'
                f'{self.exported_at.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}'
                '</span></div>'
            ),
            "footer_template": "<div></div>",
        }


def add_page_numbers(writer: PdfWriter, options: PdfOptions):
    """number the final document, regardless of chunk"""
    if not options.page_numbers:
        return
    total = len(writer.pages)
    for number, page in enumerate(writer.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        overlay = BytesIO()
        drawing = canvas.Canvas(overlay, pagesize=(width, height))
        drawing.setFont("Helvetica", 9)
        drawing.drawCentredString(width / 2, 20, f"Page {number} of {total}")
        drawing.save()
        overlay.seek(0)
        page.merge_page(PdfReader(overlay).pages[0])


def finish_pdf(data: bytes, options: PdfOptions) -> bytes:
    if not options.page_numbers:
        return data
    writer = PdfWriter()
    writer.append(BytesIO(data))
    add_page_numbers(writer, options)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
