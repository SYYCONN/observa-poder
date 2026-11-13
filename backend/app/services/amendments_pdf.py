"""Geração do relatório PDF de emendas de um parlamentar."""

import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.integrations.portal_transparencia.open_data import PORTAL_AMENDMENTS_OPEN_DATA_URL

NAVY = colors.HexColor("#07152f")
INK = colors.HexColor("#12213f")
MUTED = colors.HexColor("#657896")
GREEN = colors.HexColor("#007f62")
PALE_GREEN = colors.HexColor("#e9f8f2")
PALE_BLUE = colors.HexColor("#f1f5f9")
LINE = colors.HexColor("#dbe4ee")
PAPER = colors.HexColor("#f8fafc")
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "de-olho-na-politica.png"


def _text(value) -> str:
    return escape(str(value or ""))


def _money(value) -> str:
    if value is None:
        return "Não informado"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _short_money(value) -> str:
    if value is None:
        return "Não informado"
    return _money(value).replace("R$ ", "")


def _complete_sum(rows, attribute: str):
    values = [getattr(row, attribute) for row in rows]
    if not values or any(value is None for value in values):
        return None
    return sum(values, 0)


def _paragraph(value, style):
    return Paragraph(_text(value), style)


def _header_footer(canvas, document):
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, 14 * mm, width - document.rightMargin, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        document.leftMargin,
        9 * mm,
        "De Olho na Política · dados públicos: Portal da Transparência (CGU) · portaldatransparencia.gov.br",
    )
    canvas.drawRightString(width - document.rightMargin, 9 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_amendments_pdf(person, mandate, year: int, rows) -> bytes:
    """Renderiza um relatório institucional com resumo e registros detalhados."""

    rows = list(rows)
    committed = _complete_sum(rows, "committed_amount")
    liquidated = _complete_sum(rows, "liquidated_amount")
    paid = _complete_sum(rows, "paid_amount")
    collected_values = [row.collected_at for row in rows if row.collected_at]
    collected_at = (
        max(collected_values).astimezone(ZoneInfo("America/Sao_Paulo")).strftime(
            "%d/%m/%Y às %H:%M"
        )
        if collected_values
        else "Não informado"
    )
    generated_at = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M")
    mandate_label = " · ".join(
        value for value in [
            "Deputado federal" if person.source == "camara" else "Senador",
            mandate.party if mandate else None,
            mandate.state if mandate else None,
            f"ID {person.external_id}",
        ] if value
    )

    page_width, _ = landscape(A4)
    content_width = page_width - 32 * mm
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=19 * mm,
        title=f"Emendas de {person.name} · {year}",
        author="De Olho na Política",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21,
        leading=25, textColor=NAVY, spaceAfter=2,
    )
    eyebrow_style = ParagraphStyle(
        "Eyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, textColor=GREEN, tracking=1.4,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.7,
        leading=12, textColor=MUTED,
    )
    small_style = ParagraphStyle(
        "Small", parent=body_style, fontSize=7.4, leading=9.3,
    )
    table_header_style = ParagraphStyle(
        "TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2,
        leading=8.5, textColor=colors.white,
    )
    table_style = ParagraphStyle(
        "Table", parent=styles["Normal"], fontName="Helvetica", fontSize=7.1,
        leading=8.6, textColor=INK,
    )
    table_money_style = ParagraphStyle(
        "TableMoney", parent=table_style, alignment=TA_RIGHT,
    )
    kpi_label_style = ParagraphStyle(
        "KpiLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2,
        leading=9, textColor=GREEN, tracking=0.7,
    )
    kpi_value_style = ParagraphStyle(
        "KpiValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15,
        leading=18, textColor=NAVY,
    )
    kpi_caption_style = ParagraphStyle(
        "KpiCaption", parent=styles["Normal"], fontName="Helvetica", fontSize=6.6,
        leading=8, textColor=MUTED,
    )
    right_style = ParagraphStyle("Right", parent=body_style, alignment=TA_RIGHT)
    story = []

    logo = Image(str(LOGO_PATH), width=20 * mm, height=20 * mm) if LOGO_PATH.exists() else Spacer(20 * mm, 20 * mm)
    header = Table(
        [[logo, [Paragraph("RELATÓRIO INSTITUCIONAL", eyebrow_style), Paragraph("Emendas parlamentares", title_style)],
          Paragraph(f"Ano-base<br/><b>{year}</b><br/><font size=7>Gerado em {generated_at}</font>", right_style)]],
        colWidths=[24 * mm, content_width - 76 * mm, 52 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([header, Spacer(1, 4 * mm)])

    profile = Table(
        [[Paragraph(_text(person.name), ParagraphStyle("ProfileName", parent=title_style, fontSize=18, leading=22, textColor=colors.white)),
          Paragraph(_text(mandate_label), ParagraphStyle("ProfileMeta", parent=body_style, textColor=colors.HexColor("#c9d8eb"))),
          Paragraph("BASE OFICIAL CONSULTADA", ParagraphStyle("ProfileTag", parent=eyebrow_style, textColor=colors.HexColor("#74e6c5"), alignment=TA_RIGHT))]],
        colWidths=[92 * mm, content_width - 142 * mm, 50 * mm],
    )
    profile.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([profile, Spacer(1, 6 * mm)])

    story.append(Paragraph("RESUMO DAS EMENDAS", eyebrow_style))
    story.append(Spacer(1, 2 * mm))
    kpis = []
    for label, value, caption, fill in [
        (
            "TOTAL DE EMENDAS",
            f"{len(rows):,}".replace(",", "."),
            "Registros identificados no ano-base.",
            PALE_GREEN,
        ),
        (
            "VALOR EMPENHADO",
            _money(committed),
            "Valor reservado no orçamento.",
            PALE_BLUE,
        ),
        (
            "VALOR LIQUIDADO",
            _money(liquidated),
            "Despesa conferida e reconhecida.",
            PALE_BLUE,
        ),
        (
            "VALOR PAGO",
            _money(paid),
            "Valor efetivamente pago.",
            PALE_GREEN,
        ),
    ]:
        kpis.append([
            Paragraph(label, kpi_label_style),
            Paragraph(value, kpi_value_style),
            Paragraph(caption, kpi_caption_style),
        ])
    kpi_table = Table([kpis], colWidths=[content_width / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PALE_GREEN),
        ("BACKGROUND", (1, 0), (2, 0), PALE_BLUE),
        ("BACKGROUND", (3, 0), (3, 0), PALE_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    story.extend([kpi_table, Spacer(1, 4 * mm)])
    story.append(Paragraph(
        "Os valores representam o estágio de execução registrado pela fonte oficial para emendas de autoria no ano-base. "
        "Empenhado, liquidado e pago são etapas diferentes e não devem ser somadas. "
        "Quando: a base aberta informa o ano da emenda; não há uma data individual de envio nesta linha. "
        "Um total permanece como não informado quando qualquer registro do respectivo campo está ausente.", body_style
    ))
    story.extend([Spacer(1, 3 * mm), Paragraph(
        "Fonte responsável: Portal da Transparência do Governo Federal (CGU)<br/>"
        f"Período representado: ano-base {_text(year)}<br/>"
        f"Coletado pelo portal em: {_text(collected_at)}<br/>"
        f'Consulta original: <link href="{PORTAL_AMENDMENTS_OPEN_DATA_URL}" color="#007f62">{_text(PORTAL_AMENDMENTS_OPEN_DATA_URL)}</link>',
        body_style,
    )])
    story.extend([Spacer(1, 6 * mm), Paragraph("REGISTROS DETALHADOS", eyebrow_style), Spacer(1, 2 * mm)])

    header_row = [
        "Código", "Ano", "Tipo", "Destino", "Programa / ação", "Empenhado", "Liquidado", "Pago"
    ]
    table_rows = [[Paragraph(_text(value), table_header_style) for value in header_row]]
    for row in rows:
        program_action = "<b>%s</b><br/>%s" % (_text(row.program_name or "Programa não informado"), _text(row.action_name or "Ação não informada"))
        table_rows.append([
            _paragraph(row.external_id, table_style),
            _paragraph(row.year, table_style),
            _paragraph(row.amendment_type or "Não informado", small_style),
            _paragraph(" · ".join(filter(None, [row.locality, row.municipality, row.state])) or "Não informado", small_style),
            Paragraph(program_action, small_style),
            _paragraph(_short_money(row.committed_amount), table_money_style),
            _paragraph(_short_money(row.liquidated_amount), table_money_style),
            _paragraph(_short_money(row.paid_amount), table_money_style),
        ])
    detail_table = Table(
        table_rows,
        repeatRows=1,
        colWidths=[23 * mm, 11 * mm, 35 * mm, 38 * mm, 73 * mm, 25 * mm, 25 * mm, 25 * mm],
    )
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm),
    ]))
    story.append(detail_table)
    document.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output.getvalue()
