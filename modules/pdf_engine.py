from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Importamos Image con un alias para evitar el conflicto que tenías
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime, timedelta
from modules.utils import formatear_codigo
import os


class NumeracionDIAN(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Método que se ejecuta al final para poner el total de páginas"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        # Aquí definimos el formato final: "Página 1 de 2"
        self.setFont("Helvetica-Bold", 9)
        self.drawRightString(
            200 * mm, 15 * mm, f"Página {self._pageNumber} de {page_count}"
        )


class PDFEngine:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.path_logo = "assets/logo.png"

    def draw_watermark(self, canvas, doc):
        """Marca de agua gigante (90% de la hoja) y proporcional"""
        if os.path.exists(self.path_logo):
            from reportlab.lib.pagesizes import letter

            ancho_pag, alto_pag = letter
            canvas.saveState()

            canvas.setFillAlpha(0.03)  # Más tenue porque será muy grande

            # 90% del ancho de la página
            ancho_marca = ancho_pag * 0.9
            # El alto se calcula proporcional (asumiendo relación 1.5 o similar)
            # Para que sea automático, usamos preserveAspectRatio más adelante
            alto_marca = alto_pag * 0.6

            x_centrado = (ancho_pag - ancho_marca) / 2
            y_centrado = (alto_pag - alto_marca) / 2

            canvas.drawImage(
                self.path_logo,
                x_centrado,
                y_centrado,
                width=ancho_marca,
                height=alto_marca,
                preserveAspectRatio=True,
                anchor="c",  # Centrado interno
                mask="auto",
            )
            canvas.restoreState()

    def dibujar_pie_y_pagina(self, canvas, doc):
        """Mantiene la marca de agua. La numeración la maneja NumeracionDIAN."""
        canvas.saveState()
        # Mantenemos tu logo de fondo intacto
        self.draw_watermark(canvas, doc)
        canvas.restoreState()

    def generar_documento(
        self,
        tipo,
        num_doc,
        fecha,
        cliente_data,
        items_carrito,
        info_financiera,
        cufe=None,
    ):
        subfolder = "facturas" if "FACTURA" in tipo else "cotizaciones"
        folder_path = f"exports/{subfolder}"

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        nombre_archivo = f"{folder_path}/{tipo.replace(' ', '_')}_{num_doc}.pdf"

        doc = SimpleDocTemplate(
            nombre_archivo,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=50,
        )
        story = []

        # --- 1. ESTILOS (ORDEN LÓGICO Y COMPLETO) ---
        # Definimos la base primero para que todos los demás puedan heredar de ella
        style_normal = self.styles["Normal"]

        # 1. Estilo para títulos azules "EMPRESA" y "CLIENTE"
        style_azul = ParagraphStyle(
            "Azul",
            parent=style_normal,
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1A365D"),
            leading=14,
            spaceAfter=2,
        )

        # 2. Estilos para el Encabezado (Logo y Empresa)
        style_empresa = ParagraphStyle(
            "Emp",
            parent=style_normal,
            fontSize=10,
            leading=12,
            leftIndent=0,
            spaceBefore=0,
            spaceAfter=0,
        )

        # 3. Estilos para la información del Documento (No. y Fecha)
        style_titulo = ParagraphStyle(
            "T_Gen",
            parent=style_normal,
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.HexColor("#1A365D"),
            leading=20,
        )
        style_titulo_doc = ParagraphStyle(
            "T_Doc",
            parent=style_normal,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=20,
            alignment=2,
        )
        style_doc_derecha = ParagraphStyle(
            "DocDer",
            parent=style_normal,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=2,
        )

        # 4. Estilos para el Cliente
        style_cliente_derecha = ParagraphStyle(
            "CliDer", parent=style_normal, fontSize=10, leading=14, alignment=2
        )
        style_cliente_lista = ParagraphStyle(
            "Cli", parent=style_normal, fontSize=10, leading=14, alignment=0
        )

        # 5. Estilos para la Tabla y Legales
        style_t_head = ParagraphStyle(
            "TH",
            parent=style_normal,
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.white,
        )
        style_sub = ParagraphStyle(
            "S",
            parent=style_normal,
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4A5568"),
        )
        style_legal = ParagraphStyle(
            "L",
            parent=style_normal,
            fontName="Helvetica-Oblique",
            fontSize=7,
            alignment=1,
            textColor=colors.HexColor("#718096"),
        )

        style_cufe = ParagraphStyle(
            "CUFE",
            parent=style_normal,
            fontSize=7,
            leading=8,
            textColor=colors.grey,
            alignment=1,
            splitLongWords=True,
        )
        # --- 2. ENCABEZADO (Logo Gigante + Empresa + Info Doc) ---
        # --- 2. ENCABEZADO ---
        hora_actual = datetime.now().strftime("%H:%M:%S")

        # Título idóneo DIAN
        titulo_display = (
            "DOCUMENTO EQUIVALENTE A FACTURA DE VENTA"
            if "FACTURA" in tipo.upper()
            else tipo
        )

        # ENCABEZADO
        header_text = Paragraph(
            f"<font color='#1A365D'><b>EMPRESA EMISORA</b></font><br/>"
            "<b>DISTRIBUCIONES INDUSTRIALES FERREENVIOS DEL META</b><br/>"
            "Nit: 1.121.937.188-4<br/>"
            "Calle 17S 12-19E B. Sosiego, Villavicencio<br/>"
            "<b>Actividad Económica: 4663</b><br/>"  # Idoneidad
            "Persona Natural - No Responsable de IVA<br/>"
            "<i>Resolución de Facturación: Pendiente de trámite</i>",  # Marcador de posición
            style_empresa,
        )

        doc_info = Paragraph(
            f"<b>{titulo_display}</b><br/>"
            f"No: {num_doc}<br/>"
            f"Fecha: {fecha}<br/>"
            f"Hora: {hora_actual}",
            style_titulo_doc,
        )
        # CREACIÓN DE LA TABLA (Definición obligatoria antes de usarla)
        if os.path.exists(self.path_logo):
            img = RLImage(self.path_logo, width=220, height=110, kind="proportional")
            header_data = [[img, header_text, doc_info]]
            col_widths = [200, 210, 130]
        else:
            header_data = [[header_text, doc_info]]
            col_widths = [410, 130]

        header_table = Table(header_data, colWidths=col_widths)
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
                ]
            )
        )

        # (Aquí va la lógica de la tabla header_table que ya tienes)
        story.append(header_table)
        story.append(Spacer(1, 15))

        # --- 3. SECCIÓN DE CLIENTE (Mejora Integrada y Bien Indentada) ---
        c_nombre = cliente_data.get("nombre", "Consumidor Final")
        c_nit = cliente_data.get("nit", "2222222222")
        c_dir = cliente_data.get("dir", "N/A")
        c_tel = cliente_data.get("tel", "N/A")
        c_mail = cliente_data.get("email", "N/A")

        col_cliente_1 = (
            f"<font color='#1A365D'><b>ADQUIRIENTE / CLIENTE</b></font><br/>"
            f"<b>Nombre:</b> {c_nombre}<br/>"
            f"<b>NIT/CC:</b> {c_nit}"
        )

        col_cliente_2 = (
            f"<br/>"
            f"<b>Dirección:</b> {c_dir}<br/>"
            f"<b>Tel:</b> {c_tel} | <b>Email:</b> {c_mail}"
        )

        cliente_table_data = [
            [
                Paragraph(col_cliente_1, style_cliente_lista),
                Paragraph(col_cliente_2, style_cliente_lista),
            ]
        ]

        c_table = Table(cliente_table_data, colWidths=[270, 270])
        c_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        story.append(c_table)

        # --- 4. FORMA DE PAGO (Debajo de la línea del cliente) ---
        forma_pago = "CONTADO"
        story.append(Spacer(1, 5))
        story.append(Paragraph(f"<b>Forma de Pago:</b> {forma_pago}", style_normal))
        story.append(Spacer(1, 10))

        # --- 4. TABLA DE PRODUCTOS ---
        tabla_data = [
            [
                Paragraph("<b>Cód</b>", style_t_head),
                Paragraph("<b>Descripción</b>", style_t_head),
                Paragraph("<b>Categoría</b>", style_t_head),
                Paragraph("<b>Cant</b>", style_t_head),
                Paragraph("<b>Unitario</b>", style_t_head),
                Paragraph("<b>Total</b>", style_t_head),
            ]
        ]

        for item in items_carrito:
            cat = item.get("categoria") or "General"
            tabla_data.append(
                [
                    Paragraph(str(item["cod"]), style_sub),
                    Paragraph(item["desc"], style_sub),
                    Paragraph(str(cat), style_sub),
                    Paragraph(str(item["cant"]), style_sub),
                    Paragraph(f"${item['precio']:,.0f}", style_sub),
                    Paragraph(f"${item['total']:,.0f}", style_sub),
                ]
            )

        # Desglose de totales al final de la tabla
        tabla_data.append(
            [
                "",
                "",
                "",
                "",
                Paragraph("<b>SUBTOTAL:</b>", style_sub),
                Paragraph(f"${info_financiera['subtotal']:,.0f}", style_sub),
            ]
        )
        tabla_data.append(
            [
                "",
                "",
                "",
                "",
                Paragraph(f"<b>IVA ({info_financiera['p_iva']}%):</b>", style_sub),
                Paragraph(f"${info_financiera['v_iva']:,.0f}", style_sub),
            ]
        )

        # MEJORA: Mostrar el flete si es mayor a 0
        v_flete = info_financiera.get("flete", 0)
        if v_flete > 0:
            tabla_data.append(
                [
                    "",
                    "",
                    "",
                    "",
                    Paragraph("<b>FLETE:</b>", style_sub),
                    Paragraph(f"${v_flete:,.0f}", style_sub),
                ]
            )

        tabla_data.append(
            [
                "",
                "",
                "",
                "",
                Paragraph("<b>TOTAL NETO:</b>", style_sub),
                Paragraph(f"<b>${info_financiera['total']:,.0f}</b>", style_sub),
            ]
        )
        i_table = Table(tabla_data, colWidths=[50, 215, 70, 35, 80, 80])
        i_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
                    (
                        "ALIGN",
                        (3, 0),
                        (-1, -1),
                        "RIGHT",
                    ),  # Cantidad y precios a la derecha
                    ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#E2E8F0")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(i_table)
        story.append(Spacer(1, 35))

        # --- 5. PIE DE PÁGINA DINÁMICO (VERSIÓN ÚNICA E IDÓNEA) ---
        from modules.legal_logic import LegalLogic

        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        except:
            fecha_dt = datetime.now()

        story.append(Spacer(1, 10))

        # LÓGICA CONDICIONAL: Cotización vs Factura
        if "COTIZACIÓN" in tipo.upper():
            vencimiento = (fecha_dt + timedelta(days=15)).strftime("%Y-%m-%d")
            ley_texto = (
                f"ESTA COTIZACIÓN ES VÁLIDA POR 15 DÍAS (VENCE EL: {vencimiento}). <br/>"
                "NO CONSTITUYE UNA FACTURA ELECTRÓNICA NI OBLIGACIÓN DE COBRO IVA. <br/>"
                "PRECIOS SUJETOS A CAMBIOS SIN PREVIO AVISO SEGÚN DISPONIBILIDAD. <br/>"
                "DOCUMENTO INFORMATIVO - NO RESPONSABLE DE IVA (RÉGIMEN SIMPLIFICADO)."
            )
            # En cotización NO se agrega párrafo de ACEPTACIÓN
        else:
            vencimiento = (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")
            ley_texto = (
                f"ESTA FACTURA TIENE UN VENCIMIENTO DE 30 DÍAS (FECHA LÍMITE: {vencimiento}). <br/>"
                "EMISOR NO RESPONSABLE DE IVA - RÉGIMEN SIMPLIFICADO. <br/>"
                "ASIMILADO A FACTURA DE VENTA (ART. 616-1 ESTATUTO TRIBUTARIO Y ART. 774 COD. COMERCIO). <br/>"
                "PERSONA NATURAL NO RESPONSABLE DE IVA."
            )

            # SOLO PARA FACTURAS: Agregamos la cláusula de aceptación
            story.append(
                Paragraph(
                    "<b>ACEPTACIÓN:</b> La firma de este documento constituye la aceptación de la mercancía "
                    "a entera satisfacción y la obligación de pago de la misma bajo las condiciones pactadas.",
                    style_legal,
                )
            )
            story.append(Spacer(1, 10))

        # Agregamos la ley de vencimiento correspondiente
        story.append(Paragraph(ley_texto, style_legal))

        # BLOQUE DIAN (Solo si hay CUFE y es Factura)
        if cufe and "FACTURA" in tipo.upper():
            story.append(Spacer(1, 15))
            path_qr = LegalLogic.generar_qr_dian(
                tipo, num_doc, cufe, info_financiera["total"]
            )
            img_qr = RLImage(path_qr, width=70, height=70)
            texto_dian = f"<b>Documento Equivalente a Factura Electrónica de Venta</b><br/>CUFE: {cufe}"

            dian_table = Table(
                [[img_qr, Paragraph(texto_dian, style_cufe)]], colWidths=[80, 370]
            )
            dian_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(dian_table)

        # CRÉDITOS FINALES
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "Software de Facturación: FerreEnvios v2.0 - Desarrollador: Diego Martínez",
                style_legal,
            )
        )

        # --- CONSTRUCCIÓN FINAL ---
        # Usamos dibujar_pie_y_pagina para el logo
        # Usamos canvasmaker=NumeracionDIAN para el "Página 1 de X"
        doc.build(
            story,
            onFirstPage=self.dibujar_pie_y_pagina,
            onLaterPages=self.dibujar_pie_y_pagina,
            canvasmaker=NumeracionDIAN,
        )

        return nombre_archivo
