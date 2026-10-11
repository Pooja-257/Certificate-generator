"""PDF generation with ReportLab. Knows nothing about the database or FastAPI."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from app.core.config import settings

INK = HexColor("#10272E")
BRASS = HexColor("#B07D2B")
MUTED = HexColor("#5B6B70")
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
CENTER_X = PAGE_WIDTH / 2


class CertificateGenerationError(Exception):
    """Raised when one certificate cannot be produced. The message is safe to show to users."""


@dataclass(frozen=True)
class CertificateData:
    certificate_id: int
    job_id: int
    recipient_name: str
    course: str
    certificate_title: str
    event_name: str
    organization_name: str
    issue_date: date

    @property
    def reference(self) -> str:
        return f"CERT-{self.job_id:04d}-{self.certificate_id:05d}"


def build_certificate_path(certificate_id: int) -> Path:
    """The only place a file path is built, and it uses just the numeric ID."""
    return settings.certificate_dir / f"certificate_{certificate_id}.pdf"


def format_date(value: date) -> str:
    return f"{value.day:02d} {value.strftime('%B %Y')}"


def _check_renderable(data: CertificateData) -> None:
    """ReportLab's built-in fonts only cover Western (cp1252) characters."""
    for label, text in (("name", data.recipient_name), ("course", data.course),
                        ("event", data.event_name), ("organization", data.organization_name),
                        ("title", data.certificate_title)):
        try:
            text.encode("cp1252")
        except UnicodeEncodeError as exc:
            raise CertificateGenerationError(
                f"The {label} contains characters the certificate font cannot display."
            ) from exc


def _fit_size(text: str, font: str, size: float, max_width: float, min_size: float = 12) -> float:
    while size > min_size and stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _centered(c: Canvas, text: str, y: float, font: str, size: float, color=INK, max_width: float = 640) -> None:
    c.setFont(font, _fit_size(text, font, size, max_width))
    c.setFillColor(color)
    c.drawCentredString(CENTER_X, y, text)


def _draw_frame(c: Canvas) -> None:
    c.setStrokeColor(BRASS)
    c.setLineWidth(3)
    c.rect(24, 24, PAGE_WIDTH - 48, PAGE_HEIGHT - 48)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.rect(34, 34, PAGE_WIDTH - 68, PAGE_HEIGHT - 68)
    c.setFillColor(BRASS)
    for x in (34, PAGE_WIDTH - 34):  # small squares on the corners of the inner frame
        for y in (34, PAGE_HEIGHT - 34):
            c.rect(x - 4, y - 4, 8, 8, fill=1, stroke=0)


def _draw_divider(c: Canvas, y: float) -> None:
    c.setStrokeColor(BRASS)
    c.setLineWidth(1)
    c.line(CENTER_X - 120, y, CENTER_X - 10, y)
    c.line(CENTER_X + 10, y, CENTER_X + 120, y)
    c.setFillColor(BRASS)
    c.saveState()
    c.translate(CENTER_X, y)
    c.rotate(45)
    c.rect(-3.5, -3.5, 7, 7, fill=1, stroke=0)
    c.restoreState()


def _draw_seal(c: Canvas, x: float, y: float) -> None:
    c.setFillColor(BRASS)
    c.circle(x, y, 36, fill=1, stroke=0)
    c.setStrokeColor(white)
    c.setLineWidth(1.2)
    c.circle(x, y, 29, fill=0, stroke=1)
    c.setFillColor(white)
    c.setFont("Times-Bold", 22)
    c.drawCentredString(x, y - 7, "C")


def _draw_footer_item(c: Canvas, x: float, value: str, label: str, y: float = 100) -> None:
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.line(x - 90, y + 16, x + 90, y + 16)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x, y, value)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawCentredString(x, y - 14, label)


def _draw(c: Canvas, data: CertificateData) -> None:
    _draw_frame(c)

    _centered(c, data.organization_name.upper(), PAGE_HEIGHT - 90, "Helvetica-Bold", 13, BRASS)

    _centered(c, data.certificate_title.upper(), PAGE_HEIGHT - 145, "Times-Bold", 38, INK)
    _draw_divider(c, PAGE_HEIGHT - 168)

    _centered(c, "This certificate is proudly presented to", PAGE_HEIGHT - 210, "Helvetica", 13, MUTED)
    _centered(c, data.recipient_name.upper(), PAGE_HEIGHT - 262, "Times-BoldItalic", 42, INK, max_width=600)
    c.setStrokeColor(BRASS)
    c.setLineWidth(0.8)
    c.line(CENTER_X - 200, PAGE_HEIGHT - 276, CENTER_X + 200, PAGE_HEIGHT - 276)

    _centered(c, "for successfully participating in", PAGE_HEIGHT - 310, "Helvetica", 13, MUTED)
    _centered(c, data.course, PAGE_HEIGHT - 342, "Helvetica-Bold", 22, INK)
    _centered(c, f"as part of {data.event_name}, organized by {data.organization_name}.",
              PAGE_HEIGHT - 370, "Helvetica", 13, MUTED)

    _draw_footer_item(c, 170, format_date(data.issue_date), "Date of issue")
    _draw_seal(c, CENTER_X, 108)
    _draw_footer_item(c, PAGE_WIDTH - 170, data.reference, "Certificate ID")


def generate_certificate_pdf(data: CertificateData, output_path: Path) -> Path:
    """Render one certificate to output_path. Writes to a temp file first so a crash never leaves a broken PDF."""
    _check_renderable(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".pdf.tmp")
    try:
        canvas = Canvas(str(temp_path), pagesize=landscape(A4))
        canvas.setTitle(f"{data.certificate_title} - {data.recipient_name}")
        canvas.setAuthor(data.organization_name)
        _draw(canvas, data)
        canvas.showPage()
        canvas.save()
        temp_path.replace(output_path)
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise CertificateGenerationError("The PDF could not be rendered.") from exc
    return output_path
