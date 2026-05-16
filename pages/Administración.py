import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import csv

def obtener_ruta_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "ferreteria_final.db")

def show():
    st.set_page_config(page_title="Administración - FerreEnvios", layout="wide")
    st.header("⚖️ Panel de Control Administrativo")
    db_path = obtener_ruta_db()

    if 'pdf_listo' not in st.session_state:
        st.session_state.pdf_listo = None
        
    # 1. Definimos las pestañas primero
    tab_pagos, tab_historial, tab_config = st.tabs([
        "💰 Liquidación y Utilidades", 
        "📅 Historial Diario", 
        "⚙️ Configuración API"
    ])

    # --- PESTAÑA 1: LIQUIDACIÓN ---
    with tab_pagos:
        col1, col2 = st.columns(2)
        with col1:
            mes = st.selectbox("Mes", ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"], index=4)
        with col2:
            anio = st.selectbox("Año", ["2025", "2026"], index=1)
        
        if st.button("📊 Generar Reporte y Calcular Utilidad", use_container_width=True):
            mostrar_analitica(db_path, mes, anio)
            st.markdown("---")
            mostrar_resumen_pagos(db_path, mes, anio)

    # --- PESTAÑA 2: HISTORIAL ---
    with tab_historial:
        st.subheader("🔎 Consultar Ventas y Cotizaciones")
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            fecha_sel = st.date_input("Selecciona el día")
        with col_f2:
            incluir_coti = st.toggle("Ver Cotizaciones", value=False)
        
        mostrar_historial_dia(db_path, str(fecha_sel), incluir_coti)

    # --- PESTAÑA 3: CONFIGURACIÓN (Aquí es donde corregimos la repetición) ---
    with tab_config:
        st.subheader("⚙️ Configuración de Conexión Siigo / DIAN")
        try:
            conn = sqlite3.connect(db_path)
            # Consultamos los datos actuales
            config_actual = pd.read_sql_query("SELECT * FROM configuracion WHERE id = 1", conn).iloc[0]
            conn.close()

            # El formulario DEBE estar dentro de este 'with tab_config'
            with st.form("form_api_config"):
                user_siigo = st.text_input("Usuario Siigo (Email)", value=config_actual.get('email_siigo', ""))
                api_key = st.text_input("Access Key (API Token)", value=config_actual.get('clave_tecnica', ""), type="password")
                ambiente = st.selectbox("Ambiente", ["Pruebas / Sandbox", "Producción"], 
                                        index=0 if str(config_actual.get('ambiente')) == '1' else 1)
                
                if st.form_submit_button("Guardar Configuración"):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE configuracion 
                        SET email_siigo = ?, clave_tecnica = ?, ambiente = ? 
                        WHERE id = 1
                    """, (user_siigo, api_key, '1' if ambiente == "Pruebas / Sandbox" else '2'))
                    conn.commit()
                    conn.close()
                    st.success("✅ Configuración actualizada con éxito.")
        except Exception as e:
            st.error(f"Error al cargar la configuración: {e}")

def mostrar_analitica(db_path, mes, anio):
    fecha_filtro = f"{anio}-{mes}%"
    try:
        conn = sqlite3.connect(db_path)
        query = '''
            SELECT 
                SUM(v.total) as venta_total,
                SUM(d.cantidad * d.costo_proveedor) as costo_total
            FROM detalle_ventas d
            JOIN historial_ventas v ON d.numero_doc = v.numero_doc
            WHERE v.fecha LIKE ? AND v.tipo_doc = 'FACTURA DE VENTA'
        '''
        df_met = pd.read_sql_query(query, conn, params=(fecha_filtro,))
        conn.close()

        if not df_met.empty and df_met['venta_total'][0] is not None:
            venta, costo = df_met['venta_total'][0], df_met['costo_total'][0]
            utilidad = venta - costo
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos (Caja)", f"${int(venta):,}")
            m2.metric("Costo Socio", f"-${int(costo):,}", delta_color="inverse")
            m3.metric("Utilidad Neta", f"${int(utilidad):,}")
            st.progress(min(utilidad/venta, 1.0) if venta > 0 else 0, text=f"Margen: {round((utilidad/venta)*100, 2)}%")
    except Exception as e:
        st.error(f"Error analítica: {e}")

def mostrar_resumen_pagos(db_path, mes, anio):
    fecha_filtro = f"{anio}-{mes}%"
    try:
        conn = sqlite3.connect(db_path)
        # Consulta con GROUP BY para evitar las repeticiones que veíamos en tus fotos
        query = '''
            SELECT 
                v.numero_doc as "Factura", 
                v.fecha as "Fecha", 
                d.descripcion as "Producto", 
                SUM(d.cantidad) as "Cant", 
                d.costo_proveedor as "Costo Unit",
                SUM(d.cantidad * d.costo_proveedor) as "Total"
            FROM detalle_ventas d
            JOIN historial_ventas v ON d.numero_doc = v.numero_doc
            WHERE v.fecha LIKE ? AND v.tipo_doc = 'FACTURA DE VENTA'
            GROUP BY v.numero_doc, d.codigo_producto
        '''
        df = pd.read_sql_query(query, conn, params=(fecha_filtro,))
        conn.close()

        if not df.empty:
            st.write("### Detalle de Liquidación")
            st.dataframe(df.style.format({"Costo Unit": "${:,.0f}", "Total": "${:,.0f}"}), 
                         use_container_width=True, hide_index=True)
            
            gran_total = df["Total"].sum()
            st.info(f"💰 **Total Acumulado para Pago:** ${int(gran_total):,} COP")

            # GENERACIÓN DE EXCEL CON OPENPYXL (No requiere xlsxwriter)
            output = io.BytesIO()
            # Cambiamos engine a openpyxl
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Reporte_Socio')
                
                # Ajustamos formato directamente con la hoja de openpyxl
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Socio']
                
                # 🚀 MEJORA: Definir formato de moneda
                formato_moneda = '"$"#,##0'
                
                # Aplicar formato a las columnas E (Costo Unit) y F (Total)
                # Recorremos desde la fila 2 hasta el final de los datos
                for row in range(2, len(df) + 2):
                    worksheet.cell(row=row, column=5).number_format = formato_moneda # Costo Unit
                    worksheet.cell(row=row, column=6).number_format = formato_moneda # Total
                
                # Determinamos la última fila para poner el total
                last_row = len(df) + 2
                
                # Escribimos el Total al final
                worksheet.cell(row=last_row, column=5, value="TOTAL A TRANSFERIR:")
                celda_total = worksheet.cell(row=last_row, column=6, value=gran_total)
                
                # Opcional: Formato básico de moneda para el total en el Excel
                celda_total.number_format = '"$"#,##0'

            st.download_button(
                label="📥 Descargar Reporte en EXCEL",
                data=output.getvalue(),
                file_name=f"Liquidacion_Socio_{mes}_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.warning("No hay datos para exportar.")
    except Exception as e:
        st.error(f"Error técnico al generar el archivo: {e}")

def mostrar_historial_dia(db_path, fecha, incluir_coti):
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # --- SECCIÓN 1: TABLA DE VENTAS DEL DÍA (Mantenemos tu vista actual) ---
        tipos = "('FACTURA DE VENTA', 'COTIZACIÓN')" if incluir_coti else "('FACTURA DE VENTA')"
        query_hoy = f"SELECT fecha, tipo_doc as Tipo, numero_doc as Num, cliente_nombre as Cliente, total FROM historial_ventas WHERE fecha = ? AND tipo_doc IN {tipos}"
        df_hoy = pd.read_sql_query(query_hoy, conn, params=(fecha,))

        if not df_hoy.empty:
            st.success(f"💰 Venta Real Hoy: ${int(df_hoy[df_hoy['Tipo'] == 'FACTURA DE VENTA']['total'].sum()):,} COP")
            
            
            def color_tipo(val):
                if val == 'FACTURA DE VENTA': return 'background-color: #D4EFDF' # Verde
                if val == 'COTIZACIÓN': return 'background-color: #FCF3CF'      # Naranja
                return ''

            # Asegúrate de que el st.dataframe use el estilo:
            st.dataframe(
                df_hoy.style.applymap(color_tipo, subset=['Tipo']).format({"total": "${:,.0f}"}), 
                use_container_width=True, 
                hide_index=True
         )
        
        else:
            st.info(f"No hay registros de ventas para hoy ({fecha}).")

        # --- SECCIÓN 2: GESTIÓN PERMANENTE (BUSCADOR DINÁMICO) ---
        st.markdown("---")
        st.subheader("🛠️ Acciones de Gestión")

        # CARGA DE FACTURAS HISTÓRICAS (Para el Selector Profesional)
        # Traemos las últimas 50 facturas para que siempre haya qué elegir
        query_historial = "SELECT numero_doc, cliente_nombre FROM historial_ventas WHERE tipo_doc = 'FACTURA DE VENTA' ORDER BY numero_doc DESC LIMIT 50"
        facturas_recientes = conn.execute(query_historial).fetchall()
        # Creamos una lista formateada: "1020 - DIEGO MARTINEZ"
        lista_opciones = [f"{r['numero_doc']} - {r['cliente_nombre']}" for r in facturas_recientes]

        with st.expander("🔄 Generar Nota Crédito / Devolución", expanded=True):
            st.write("Seleccione una factura reciente o ingrese el número manualmente:")
            
            tab1, tab2 = st.tabs(["📋 Seleccionar de Lista", "🔍 Búsqueda Manual"])
            
            with tab1:
                if lista_opciones:
                    seleccion = st.selectbox("Facturas recientes (Últimas 50):", lista_opciones, key="sel_historial_global")
                    if st.button("🔄 Procesar Selección", use_container_width=True):
                        st.session_state.factura_a_devolver = seleccion.split(" - ")[0]
                else:
                    st.warning("No hay facturas en el historial.")

            with tab2:
                num_manual = st.text_input("Número de Factura específico:", placeholder="Ej: 1017")
                if st.button("🔍 Buscar Factura Manual", use_container_width=True):
                    if num_manual: st.session_state.factura_a_devolver = num_manual

        # --- SECCIÓN 3: PROCESAMIENTO (LA MÁQUINA) ---
        if "factura_a_devolver" in st.session_state:
            numero_doc = st.session_state.factura_a_devolver
            st.markdown("---")
            st.warning(f"⚠️ Gestión Activa: Factura **{numero_doc}**")
            
            # Llamamos a la lógica de devolución
            seccion_devolucion(numero_doc, db_path)
            
            if st.button("❌ Cerrar y Limpiar", use_container_width=True):
                del st.session_state.factura_a_devolver
                if "pdf_listo" in st.session_state: del st.session_state.pdf_listo
                st.rerun()
        
        conn.close()

    except Exception as e:
        st.error(f"Error historial: {e}")
        

def seccion_devolucion(numero_doc, db_path):
    # 1. Título y Preparación
    st.write(f"### 🔄 Procesando Devolución: Factura {numero_doc}")
    
    # Importamos el Manager (Esto evita errores de sqlite3 local)
    from modules.NotaCreditoManager import NotaCreditoManager
    manager = NotaCreditoManager()
    
    # 2. 🔍 CARGA DE DATOS (Usando el método profesional del Manager)
    with st.spinner("Cargando productos de la base de datos..."):
        items_en_factura = manager.obtener_productos_factura(numero_doc)
    
    if not items_en_factura:
        st.error(f"❌ No se encontraron productos registrados para la factura #{numero_doc}")
        return

    # 3. INTERFAZ DE SELECCIÓN
    st.info("Seleccione los productos y cantidades que el cliente desea devolver.")
    items_a_devolver = []
    
    # Usamos un expansor para que la interfaz se vea organizada como querías
    with st.expander(f"📦 Detalle de Productos - Factura #{numero_doc}", expanded=True):
        with st.form(f"form_nc_final_{numero_doc}"):
            for item in items_en_factura:
                col_desc, col_cant = st.columns([3, 1])
                
                with col_desc:
                    st.markdown(f"**{item['descripcion']}**")
                    st.caption(f"Comprado: {item['cantidad']} und | Precio: ${item['precio_venta']:,.0f}")
                
                with col_cant:
                    # El selector de cantidad con el límite real de la factura
                    cant_dev = st.number_input(
                        "Cant.", 
                        min_value=0, 
                        max_value=int(item['cantidad']), 
                        key=f"input_dev_{item['codigo_producto']}"
                    )
                
                if cant_dev > 0:
                    items_a_devolver.append({
                        "codigo": item['codigo_producto'],
                        "descripcion": item['descripcion'],
                        "cantidad": cant_dev,
                        "precio": item['precio_venta']
                    })

            st.markdown("---")
            motivo = st.selectbox("Motivo de la devolución", [
                "1. Devolución parcial de los bienes",
                "2. Anulación de factura electrónica",
                "3. Ajuste de precio"
            ])

            # 4. BOTÓN DE EMISIÓN (Lógica de Siigo + PDF)
            if st.form_submit_button("🚀 Emitir Nota Crédito Legal", use_container_width=True):
                if not items_a_devolver:
                    st.error("❌ Debes seleccionar al menos un producto para devolver.")
                else:
                    from modules.siigo_adapter import SiigoAdapter
                    adapter = SiigoAdapter()
                    
                    with st.spinner("Enviando a Siigo/DIAN..."):
                        exito, msg = adapter.enviar_nota_credito(numero_doc, motivo[0], items_a_devolver)
                    
                    if exito:
                        st.success(f"✅ Éxito: Nota Crédito procesada. CUNE: {msg}")
                        
# --- BLOQUE DE EXTRACCIÓN GARANTIZADA CON MEJORAS INTEGRADAS ---
                        try:
                            import sqlite3
                            conn = sqlite3.connect(db_path)
                            conn.row_factory = sqlite3.Row
                            
                            # 1. TRAER FACTURA ORIGINAL (Para asegurar precios y cliente)
                            factura_query = "SELECT * FROM historial_ventas WHERE numero_doc = ? LIMIT 1"
                            factura_row = conn.execute(factura_query, (numero_doc,)).fetchone()
                            
                            if not factura_row:
                                st.error(f"❌ Error Crítico: No se encontró la factura {numero_doc} en el historial.")
                                conn.close()
                            else:
                                # Convertimos a diccionario para manipularlo fácil
                                datos_f = dict(factura_row)
                                
                                # 2. TRAER DATOS DEL CLIENTE (Usando el nombre que viene en la factura)
                                cliente_query = "SELECT * FROM clientes WHERE TRIM(UPPER(nombre)) = TRIM(UPPER(?))"
                                cliente_row = conn.execute(cliente_query, (datos_f['cliente_nombre'],)).fetchone()
                                
                                # 3. SERIALIZACIÓN (MEJORA: Conteo real para NC-XXXX)
                                res_nc = conn.execute("SELECT COUNT(*) FROM historial_ventas WHERE tipo_doc = 'NOTA CRÉDITO'").fetchone()
                                proximo_numero = (res_nc[0] + 1) if res_nc else 1
                                serial_nc = str(proximo_numero) 
                                
                                conn.close()

                                # 4. CONSTRUCCIÓN DEL PAQUETE Y LIMPIEZA DE NOMBRE (MEJORA)
                                nombre_cliente_exacto = datos_f.get('cliente_nombre', 'CONSUMIDOR FINAL').strip().upper()
                                
                                info_cliente = dict(cliente_row) if cliente_row else {
                                    "cliente_nombre": nombre_cliente_exacto,
                                    "nit_cedula": datos_f.get('nit_cedula', '22222222'),
                                    "direccion": "S/D",
                                    "telefono": "S/N"
                                }

                                # 5. AJUSTE DE PRECIOS DE LOS ITEMS
                                items_procesados = []
                                for item in items_a_devolver:
                                    item['precio'] = item.get('precio', 0) 
                                    items_procesados.append(item)

                        except Exception as e:
                            st.error(f"❌ Error en la extracción de datos: {e}")
                        finally:
                            if 'conn' in locals():
                                conn.close()
# --- 6. ENVIAR AL MANAGER (PAQUETE BLINDADO) ---
                        try:
                            datos_para_pdf = {
                                "empresa": {
                                    "nombre": "DISTRIBUCIONES INDUSTRIALES FERREENVIOS DEL META",
                                    "nit": "1.121.937.188-4",
                                    "direccion": "Villavicencio, Meta",
                                    "regimen": "Persona Natural - No Responsable de IVA"
                                },
                                "factura": info_cliente, 
                                "cune": msg,
                                "numero_nc": serial_nc  # Viaja el número real calculado
                            }

                            from modules.printer_manager import generar_pdf_nota_credito
                            pdf_bytes = generar_pdf_nota_credito(datos_para_pdf, numero_doc, items_procesados)

                            if pdf_bytes:
                                # Nombre profesional con ceros a la izquierda (NC_0001)
                                nombre_archivo = f"NC_{serial_nc.zfill(4)}_Factura_{numero_doc}.pdf"
                                st.session_state.pdf_listo = {
                                    "data": pdf_bytes,
                                    "name": nombre_archivo
                                }
                                st.success(f"✅ Nota Crédito #NC-{serial_nc.zfill(4)} preparada para descarga.")
                                st.balloons()
                            else:
                                st.error("❌ El motor de PDF devolvió un archivo vacío. Revisa el retorno en printer_manager.py")

                        except Exception as e:
                            st.error(f"❌ Error en la generación del PDF: {e}")
                            
                            
        # EL BOTÓN DEBE ESTAR AQUÍ, BIEN AFUERA
        if "pdf_listo" in st.session_state and isinstance(st.session_state.pdf_listo, dict):
           st.download_button(
               label="📥 DESCARGAR NOTA DE CRÉDITO",
               data=st.session_state.pdf_listo.get("data", b""),
               file_name=st.session_state.pdf_listo.get("name", "Nota_Credito.pdf"),
               mime="application/pdf",
               use_container_width=True,
               key="btn_descarga_final"
            )
            
        # 4. Botón de cierre
        if st.button("Finalizar y Actualizar Vista", use_container_width=True):
            if "factura_a_devolver" in st.session_state:
                del st.session_state.factura_a_devolver
            st.rerun()

if __name__ == "__main__":
    # Asegúrate de que la función show() esté definida arriba en tu archivo
    show()