"""Geração do relatório PDF da equipe parlamentar coletada."""

import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.integrations.camara.staff import CAMARA_STAFF_URL

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "de-olho-na-politica.png"
NAVY = colors.HexColor("#07152f")
INK = colors.HexColor("#12213f")
MUTED = colors.HexColor("#657896")
GREEN = colors.HexColor("#007f62")
PALE_GREEN = colors.HexColor("#e9f8f2")
PALE_BLUE = colors.HexColor("#f1f5f9")
LINE = colors.HexColor("#dbe4ee")


def _text(value) -> str:
    return escape(str(value or ""))


def _currency(value) -> str:
    if value is None:
        return "Não informado"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _total(values) -> object:
    values = list(values)
    if not values or any(value is None for value in values):
        return None
    return sum(values, 0)


def build_staff_pdf(person, mandate, staff, staff_members=None) -> bytes:
    """Renderiza o resumo e a composição da equipe em exercício."""

    generated_at = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M")
    collected_at = staff.collected_at.astimezone(ZoneInfo("America/Sao_Paulo")).strftime(
        "%d/%m/%Y às %H:%M"
    )
    mandate_label = " · ".join(
        value
        for value in [
            "Deputado federal" if person.source == "camara" else "Senador",
            mandate.party if mandate else None,
            mandate.state if mandate else None,
            f"ID {person.external_id}",
        ]
        if value
    )
    period = f"{staff.month:02d}/{staff.year}"
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
        title=f"Equipe de {person.name} · {period}",
        author="De Olho na Política",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "StaffTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21,
        leading=25, textColor=NAVY,
    )
    eyebrow_style = ParagraphStyle(
        "StaffEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, textColor=GREEN, tracking=1.4,
    )
    body_style = ParagraphStyle(
        "StaffBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9,
        leading=13, textColor=MUTED,
    )
    right_style = ParagraphStyle("StaffRight", parent=body_style, alignment=TA_RIGHT)
    label_style = ParagraphStyle(
        "StaffLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
        leading=10, textColor=GREEN, tracking=0.7,
    )
    value_style = ParagraphStyle(
        "StaffValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=22,
        leading=26, textColor=NAVY,
    )
    caption_style = ParagraphStyle(
        "StaffCaption", parent=body_style, fontSize=8, leading=10,
    )
    profile_name = ParagraphStyle(
        "StaffProfileName", parent=title_style, fontSize=18, leading=22, textColor=colors.white
    )
    profile_meta = ParagraphStyle(
        "StaffProfileMeta", parent=body_style, textColor=colors.HexColor("#c9d8eb")
    )
    profile_tag = ParagraphStyle(
        "StaffProfileTag", parent=eyebrow_style, textColor=colors.HexColor("#74e6c5"),
        alignment=TA_RIGHT,
    )
    table_header_style = ParagraphStyle(
        "StaffTableHeader", parent=label_style, fontSize=7.5, leading=9,
    )
    table_body_style = ParagraphStyle(
        "StaffTableBody", parent=body_style, fontSize=8.5, leading=11, textColor=INK,
    )
    table_amount_style = ParagraphStyle(
        "StaffTableAmount", parent=table_body_style, alignment=TA_RIGHT,
    )
    story = []
    members = list(staff_members or [])
    gross_total = _total(member.gross_amount for member in members)
    net_total = _total(member.net_amount for member in members)
    allowances_total = _total(member.allowances_amount for member in members)

    logo = Image(str(LOGO_PATH), width=20 * mm, height=20 * mm) if LOGO_PATH.exists() else Spacer(20 * mm, 20 * mm)
    header = Table(
        [[
            logo,
            [Paragraph("RELATÓRIO INSTITUCIONAL", eyebrow_style), Paragraph("Equipe parlamentar", title_style)],
            Paragraph(f"Competência<br/><b>{period}</b><br/><font size=7>Gerado em {generated_at}</font>", right_style),
        ]],
        colWidths=[24 * mm, content_width - 76 * mm, 52 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([header, Spacer(1, 4 * mm)])

    profile = Table(
        [[
            Paragraph(_text(person.name), profile_name),
            Paragraph(_text(mandate_label), profile_meta),
            Paragraph("BASE OFICIAL CONSULTADA", profile_tag),
        ]],
        colWidths=[92 * mm, content_width - 142 * mm, 50 * mm],
    )
    profile.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([profile, Spacer(1, 7 * mm)])

    story.append(Paragraph("RESUMO DA EQUIPE", eyebrow_style))
    story.append(Spacer(1, 2 * mm))
    cards = Table(
        [[
            [Paragraph("ASSESSORES EM EXERCÍCIO", label_style), Paragraph(f"{staff.staff_count:,}".replace(",", "."), value_style), Paragraph("Total publicado para o gabinete.", caption_style)],
            [Paragraph("REMUNERAÇÃO BRUTA", label_style), Paragraph(_currency(gross_total), ParagraphStyle("StaffMoney", parent=value_style, fontSize=14, leading=18)), Paragraph("Soma dos componentes antes dos descontos obrigatórios.", caption_style)],
            [Paragraph("APÓS DESCONTOS", label_style), Paragraph(_currency(net_total), ParagraphStyle("StaffNet", parent=value_style, fontSize=14, leading=18)), Paragraph("Soma da linha oficial após descontos obrigatórios.", caption_style)],
            [Paragraph("AUXÍLIOS E OUTROS", label_style), Paragraph(_currency(allowances_total), ParagraphStyle("StaffAllowances", parent=value_style, fontSize=14, leading=18)), Paragraph("Soma dos itens publicados na categoria Outros.", caption_style)],
        ]],
        colWidths=[content_width / 4] * 4,
    )
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PALE_GREEN),
        ("BACKGROUND", (1, 0), (-1, 0), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([cards, Spacer(1, 7 * mm)])
    story.append(Paragraph("COMO LER ESTE REGISTRO", eyebrow_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        (
            "Este relatório apresenta a composição publicada para o gabinete na competência consultada. "
            "Os valores são os campos de remuneração divulgados pela Câmara; descontos pessoais que a fonte não divulga podem fazer o valor efetivamente recebido ser menor."
            if members
            else "A consulta nominal desta competência ainda não foi importada; os valores individuais serão exibidos após a próxima coleta completa."
        ),
        body_style,
    ))
    story.extend([Spacer(1, 7 * mm), Paragraph("CONSULTA OFICIAL", eyebrow_style), Spacer(1, 2 * mm)])
    source_box = Table([[
        Paragraph(
            "Fonte responsável: Câmara dos Deputados<br/>"
            f'Página oficial da equipe: <link href="{CAMARA_STAFF_URL}" color="#007f62">{_text(CAMARA_STAFF_URL)}</link><br/>'
            f"Competência representada: {_text(period)}<br/>"
            f"Coletado pelo portal em: {_text(collected_at)}<br/>"
            "Os filtros do gabinete são aplicados na consulta do perfil. Os links individuais de remuneração foram consultados na mesma competência.",
            body_style,
        ),
        Paragraph(
            "Dados organizados pelo De Olho na Política.<br/><br/>"
            "Aviso de privacidade: nomes, cargos e remunerações são republicados por sua relação "
            "com a atividade pública. O relatório não inclui CPF, endereço ou descontos pessoais. "
            "Um registro isolado não permite concluir culpa, irregularidade, intenção ou responsabilidade.",
            body_style,
        ),
    ]], colWidths=[content_width * 0.68, content_width * 0.32])
    source_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(source_box)
    if members:
        story.append(PageBreak())
        story.append(Paragraph("COMPOSIÇÃO DA EQUIPE", eyebrow_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"{len(members)} assessores encontrados na consulta oficial de {period}. "
            "A remuneração é apresentada por competência e pode mudar em uma nova coleta.",
            body_style,
        ))
        story.append(Spacer(1, 4 * mm))
        table_rows = [[
            Paragraph("NOME", table_header_style),
            Paragraph("CARGO / NÍVEL", table_header_style),
            Paragraph("BRUTA", table_header_style),
            Paragraph("APÓS DESCONTOS", table_header_style),
            Paragraph("AUXÍLIOS", table_header_style),
        ]]
        for member in members:
            role = " · ".join(value for value in [member.job_title or member.category, member.level] if value)
            table_rows.append([
                Paragraph(
                    f"{_text(member.name)}<br/><font size=7>Ref. oficial: {_text(member.external_id)}</font>",
                    table_body_style,
                ),
                Paragraph(_text(role or "Não informado"), table_body_style),
                Paragraph(_currency(member.gross_amount), table_amount_style),
                Paragraph(_currency(member.net_amount), table_amount_style),
                Paragraph(_currency(member.allowances_amount), table_amount_style),
            ])
        staff_table = LongTable(
            table_rows,
            colWidths=[content_width * 0.28, content_width * 0.25, content_width * 0.15, content_width * 0.18, content_width * 0.14],
            repeatRows=1,
        )
        staff_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALE_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), GREEN),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
        ]))
        story.append(staff_table)
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(
            "Como ler os valores: “bruta” reúne os componentes de remuneração anteriores aos descontos obrigatórios; "
            "“após descontos” reproduz a linha oficial correspondente; “auxílios” reúne os itens publicados na categoria Outros. "
            "A fonte oficial não divulga descontos pessoais, como pensão e consignações. Totais são exibidos somente quando "
            "todos os registros da competência possuem o respectivo campo; lacunas permanecem como não informadas.",
            body_style,
        ))
    def footer(canvas, current_document):
        canvas.saveState()
        width, _ = landscape(A4)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(current_document.leftMargin, 14 * mm, width - current_document.rightMargin, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(current_document.leftMargin, 9 * mm, "De Olho na Política · dados públicos: Câmara dos Deputados")
        canvas.drawRightString(width - current_document.rightMargin, 9 * mm, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
