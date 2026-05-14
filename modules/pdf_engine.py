from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os

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
            
            canvas.setFillAlpha(0.03) # Más tenue porque será muy grande
            
            # 90% del ancho de la página
            ancho_marca = ancho_pag * 0.9 
            # El alto se calcula proporcional (asumiendo relación 1.5 o similar)
            # Para que sea automático, usamos preserveAspectRatio más adelante
            alto_marca = alto_pag * 0.6 
            
            x_centrado = (ancho_pag - ancho_marca) / 2
            y_centrado = (alto_pag - alto_marca) / 2
            
            canvas.drawImage(
                self.path_logo, 
                x_centrado, y_centrado, 
                width=ancho_marca, 
                height=alto_marca, 
                preserveAspectRatio=True, 
                anchor='c', # Centrado interno
                mask='auto'
            )
            canvas.restoreState()

    def generar_documento(self, tipo, num_doc, fecha, cliente_data, items_carrito, info_financiera):
        subfolder = "facturas" if "FACTURA" in tipo else "cotizaciones"
        folder_path = f"exports/{subfolder}"
        
        if not os.path.exists(folder_path): os.makedirs(folder_path)
        nombre_archivo = f"{folder_path}/{tipo.replace(' ', '_')}_{num_doc}.pdf"
        
        doc = SimpleDocTemplate(nombre_archivo, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        
        style_normal = self.styles['Normal']
        style_titulo = ParagraphStyle('T', parent=style_normal, fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor("#1A365D"))
        style_sub = ParagraphStyle('S', parent=style_normal, fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor("#4A5568"))
        style_t_head = ParagraphStyle('TH', parent=style_normal, fontName='Helvetica-Bold', fontSize=10, textColor=colors.white)
        style_legal = ParagraphStyle('L', parent=style_normal, fontName='Helvetica-Oblique', fontSize=7, alignment=1, textColor=colors.HexColor("#718096"))

        header_text = Paragraph("<b>DISTRIBUCIONES INDUSTRIALES FERREENVIOS</b><br/>Nit: 1.121.XXX.XXX-X<br/>Villavicencio - Meta", style_sub)
        doc_info = Paragraph(f"<font size=12><b>{tipo}</b></font><br/><b>No:</b> {num_doc}<br/><b>Fecha:</b> {fecha}", style_titulo)
        
        if os.path.exists(self.path_logo):
            img = Image(self.path_logo, width=90, height=45, kind='proportional') # Logo de arriba izquierda
            header_data = [[img, header_text, doc_info]]
            # Ajustamos anchos: Imagen(120), Empresa(190), Info Doc(220)
            col_widths = [100, 250, 180]
        else:
            header_data = [[header_text, doc_info]]
            col_widths = [340, 190]
            
        header_table = Table(header_data, colWidths=col_widths)
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (-1,0), (-1,0), 'RIGHT'),
            ('LEFTPADDING', (2,0), (2,0), 30) # Empuja la info de factura a la derecha
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        # Sección de cliente persistente
        c_info = [
            [Paragraph(f"<b>CLIENTE:</b> {cliente_data.get('nombre', 'General')}", style_sub), 
             Paragraph(f"<b>NIT/CC:</b> {cliente_data.get('nit', 'N/A')}", style_sub)],
            [Paragraph(f"<b>DIR:</b> {cliente_data.get('dir', 'N/A')}", style_sub),
             Paragraph(f"<b>TEL:</b> {cliente_data.get('tel', 'N/A')}", style_sub)],
            [Paragraph(f"<b>EMAIL:</b> {cliente_data.get('email', 'N/A')}", style_sub), ""]
        ]
        c_table = Table(c_info, colWidths=[265, 265])
        story.append(c_table)
        story.append(Spacer(1, 15))

        tabla_data = [[Paragraph("<b>Cód</b>", style_t_head), Paragraph("<b>Descripción</b>", style_t_head), Paragraph("<b>Cant</b>", style_t_head), Paragraph("<b>Unitario</b>", style_t_head), Paragraph("<b>Total</b>", style_t_head)]]
        for item in items_carrito:
            tabla_data.append([Paragraph(str(item['cod']), style_sub), Paragraph(item['desc'], style_sub), Paragraph(str(item['cant']), style_sub), Paragraph(f"${item['precio']:,.0f}", style_sub), Paragraph(f"${item['total']:,.0f}", style_sub)])
            
        tabla_data.append(["", "", "", Paragraph("<b>SUBTOTAL:</b>", style_sub), Paragraph(f"${info_financiera['subtotal']:,.0f}", style_sub)])
        tabla_data.append(["", "", "", Paragraph(f"<b>IVA ({info_financiera['p_iva']}%):</b>", style_sub), Paragraph(f"${info_financiera['v_iva']:,.0f}", style_sub)])
        tabla_data.append(["", "", "", Paragraph("<b>TOTAL NETO:</b>", style_sub), Paragraph(f"<b>${info_financiera['total']:,.0f}</b>", style_sub)])

        i_table = Table(tabla_data, colWidths=[55, 275, 40, 75, 85])
        i_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), ('ALIGN', (2,0), (-1,-1), 'RIGHT'), ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor("#E2E8F0")), ('PADDING', (0,0), (-1,-1), 5)]))
        story.append(i_table)
        story.append(Spacer(1, 35))

        ley = "PERSONA NATURAL NO RESPONSABLE DE IVA. DOCUMENTO ASIMILADO A FACTURA."
        story.append(Paragraph(ley, style_legal))
        
        doc.build(story, onFirstPage=self.draw_watermark, onLaterPages=self.draw_watermark)
        return nombre_archivo