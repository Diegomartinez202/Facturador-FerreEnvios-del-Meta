from fpdf import FPDF
import os
import traceback  # Para rastrear el error exacto si ocurre

def generar_pdf_nota_credito(datos_nc, factura_original, items_devueltos):
    try:
        # --- 0. CONTROL DE ERRORES CRÍTICOS (Anti-NoneType) ---
        if datos_nc is None: datos_nc = {}
        if items_devueltos is None: items_devueltos = []
        
        # --- 1. CONFIGURACIÓN DE DATOS FIJOS (LEGAL DIAN) ---
        EMPRESA_FIJA = {
            "nombre": "DISTRIBUCIONES INDUSTRIALES FERREENVIOS DEL META",
            "nit": "1.121.937.188-4",
            "regimen": "Persona Natural - No Responsable de IVA",
            "actividad": "Actividad Económica CIIU 4663",
            "resolucion": "Resolución DIAN No. 187640000001 del 2026-01-01",
            "rango": "Rango NC-0001 al NC-9999",
            "direccion": "Villavicencio, Meta",
            "contacto": "Cel: 310 000 0000"
        }

        def limpiar(texto):
            if texto is None:
                return ""
            return str(texto).encode('latin-1', 'replace').decode('latin-1')

        # Extraer diccionarios de seguridad de forma estricta
        info_factura = datos_nc.get('factura')
        if not isinstance(info_factura, dict): 
            info_factura = {} 
        
        # Si no encuentra 'cune', busca también por 'cufe' por si la simulación cambió la llave
        cune_crudo = datos_nc.get('cune') or datos_nc.get('cufe') or "🛡️ Simulación Exitosa: CUFE-SIMULADO-FERREENVIOS-2026-TEST"
        cune_valor = limpiar(cune_crudo)
        
        # --- 2. SERIALIZACIÓN ---
        num_raw = str(datos_nc.get('numero_nc', '1'))
        num_consecutivo = f"NC-{num_raw.zfill(4)}"

        pdf = FPDF()
        pdf.add_page()
        
        # --- 3. LOGO / MARCA DE AGUA ---
        try:
            logo_path = os.path.join(os.getcwd(), "assets", "logo.png")
            if os.path.exists(logo_path):
                pdf.image(logo_path, 10, 2, 33)
            else:
                pdf.ln(10) 
        except:
            pdf.ln(10)

        # --- 4. ENCABEZADO LEGAL ---
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40) 
        pdf.cell(0, 8, limpiar(EMPRESA_FIJA["nombre"]), ln=True, align="L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(40)
        pdf.cell(0, 4, f"NIT: {EMPRESA_FIJA['nit']} | {EMPRESA_FIJA['regimen']}", ln=True, align="L")
        pdf.cell(40)
        pdf.cell(0, 4, f"{EMPRESA_FIJA['actividad']} | {EMPRESA_FIJA['direccion']}", ln=True, align="L")
        pdf.ln(10)

        # --- 5. TÍTULOS ---
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f" NOTA CRÉDITO ELECTRÓNICA No. {num_consecutivo}", 0, 1, 'L', True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, limpiar(f" Referencia Factura Afectada: {factura_original}"), ln=True)
        pdf.ln(3)

        # --- 6. DATOS DEL CLIENTE ---
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, " INFORMACIÓN DEL RECEPTOR", 0, 1, 'L', True)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(100, 5, limpiar(f"Nombre: {info_factura.get('cliente_nombre', 'Consumidor Final')}"), 0, 0)
        pdf.cell(90, 5, limpiar(f"NIT/CC: {info_factura.get('nit_cedula', 'N/A')}"), 0, 1)
        pdf.cell(100, 5, limpiar(f"Dirección: {info_factura.get('direccion', 'S/D')}"), 0, 0)
        pdf.cell(90, 5, limpiar(f"Teléfono: {info_factura.get('telefono', 'S/N')}"), 0, 1)
        pdf.ln(5)

        # --- 7. TABLA PRODUCTOS ---
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(90, 7, "Descripción", 1, 0, 'C', True)
        pdf.cell(20, 7, "Cant.", 1, 0, 'C', True)
        pdf.cell(40, 7, "Base (Sin IVA)", 1, 0, 'C', True)
        pdf.cell(40, 7, "Subtotal", 1, 1, 'C', True)

        pdf.set_font("Helvetica", "", 9)
        total_base = 0
        total_iva = 0
        
        for item in items_devueltos:
            if not item or not isinstance(item, dict): 
                continue
                
            try:
                # Sanitización estricta de números vacíos o corruptos
                raw_precio = item.get('precio', 0)
                raw_cant = item.get('cantidad', 0)
                
                precio_con_iva = float(raw_precio) if str(raw_precio).strip() != "" else 0.0
                cant = float(raw_cant) if str(raw_cant).strip() != "" else 0.0
                
                if cant == 0: 
                    continue # Evita filas vacías sin cantidad
                
                base_unitaria = precio_con_iva / 1.19
                subtotal_item_base = base_unitaria * cant
                iva_item = (precio_con_iva - base_unitaria) * cant
                
                total_base += subtotal_item_base
                total_iva += iva_item

                pdf.cell(90, 7, limpiar(item.get('descripcion', ''))[:45], 1)
                pdf.cell(20, 7, str(int(cant)), 1, 0, 'C')
                pdf.cell(40, 7, f"${base_unitaria:,.0f}", 1, 0, 'R')
                pdf.cell(40, 7, f"${subtotal_item_base:,.0f}", 1, 1, 'R')
            except Exception as e_item: 
                print(f"⚠️ Saltado ítem por error menor: {e_item}")
                continue

        # --- 8. TOTALES LEGALES ---
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(150, 6, "SUBTOTAL (Base Gravable): ", 0, 0, 'R')
        pdf.cell(40, 6, f"${total_base:,.0f}", 1, 1, 'R')
        pdf.cell(150, 6, "IVA (19%): ", 0, 0, 'R')
        pdf.cell(40, 6, f"${total_iva:,.0f}", 1, 1, 'R')
        
        pdf.set_fill_color(26, 54, 93)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(150, 7, "TOTAL DEVOLUCIÓN: ", 0, 0, 'R', True)
        pdf.cell(40, 7, f"${(total_base + total_iva):,.0f}", 1, 1, 'R', True)
        
        # --- 9. PIE DE PÁGINA ---
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 7)
        
        # Ajuste Multi-cell seguro para el CUNE largo de la DIAN
        pdf.multi_cell(0, 4, f"CUNE: {cune_valor}")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 7)
        pdf.multi_cell(0, 4, limpiar(f"{EMPRESA_FIJA['resolucion']} | {EMPRESA_FIJA['rango']}"), align='C')
        pdf.multi_cell(0, 4, limpiar("Generado por RAÍCES SYSTEM para FERREENVÍOS DEL META."), align='C')

        # Retorno clásico FPDF en modo String binario seguro
        string_pdf = pdf.output(dest='S')
        
        # Si devuelve un string de Python, lo codificamos. Si ya son bytes, se pasa directo.
        if isinstance(string_pdf, str):
            return string_pdf.encode('latin-1', 'replace')
        return bytes(string_pdf)

    except Exception as e:
        # 🚨 ESTO IMPRIMIRÁ EN TU CONSOLA LA LÍNEA EXACTA DONDE MUERE EL PDF
        print("❌ ERROR CRÍTICO EN EL MOTOR DE PDF:")
        traceback.print_exc() 
        return b""
