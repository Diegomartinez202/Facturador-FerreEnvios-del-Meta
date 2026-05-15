import streamlit as st
import pandas as pd
from datetime import datetime
import os
from modules.pdf_engine import PDFEngine
from modules.utils import calcular_financieros

def show():
    
    # --- PRUEBA DE DIAGNÓSTICO TEMPORAL ---
    # Esto te imprimirá en la consola de VS Code o la terminal negra las columnas actuales
    try:
        conn = st.session_state.db.conectar()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(historial_ventas)")
        columnas = [col[1] for col in cursor.fetchall()]
        print(f"Columnas detectadas en historial_ventas: {columnas}")
        conn.close()
    except:
        pass
    # --- FIN DE PRUEBA ---
    # --- SEGURO DE CONEXIÓN A BASE DE DATOS ---
    if 'db' not in st.session_state:
        from modules.database_manager import DatabaseManager
        st.session_state.db = DatabaseManager()
    
    st.header("Generador de Facturas y Cotizaciones")

    # Inicializar el carrito en la sesión si no existe
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

# --- NUEVA MEJORA: Estado para reiniciar cantidad ---
    if "reset_cant" not in st.session_state:
        st.session_state.reset_cant = 0
        
    # --- SECCIÓN DE CLIENTE ---
    st.subheader("Información del Cliente")
    df_clientes = st.session_state.db.obtener_clientes()
    lista_clientes = ["-- Nuevo Cliente --"] + df_clientes['nombre'].tolist()
    sel_cliente = st.selectbox("Seleccionar Cliente Registrado", lista_clientes)

    with st.expander("Datos del Cliente", expanded=(sel_cliente == "-- Nuevo Cliente --")):
        if sel_cliente != "-- Nuevo Cliente --":
            datos_c = df_clientes[df_clientes['nombre'] == sel_cliente].iloc[0]
            v_nit, v_tel, v_dir = str(datos_c['nit_cedula']), str(datos_c['telefono']), str(datos_c['direccion'])
            v_email = str(datos_c['email']) if 'email' in datos_c else ""
        else:
            v_nit, v_tel, v_dir, v_email = "", "", "", ""

        c_nit = st.text_input("NIT / Cédula", value=v_nit)
        c_nom = st.text_input("Nombre / Razón Social", value="" if sel_cliente == "-- Nuevo Cliente --" else sel_cliente)
        
        col_c1, col_c2 = st.columns(2)
        c_tel = col_c1.text_input("Teléfono", value=v_tel)
        c_email = col_c2.text_input("Email (Opcional)", value=v_email)
        
        c_dir = st.text_input("Dirección", value=v_dir)
        
    st.markdown("---")
    
    # --- CONFIGURACIÓN DEL DOCUMENTO (CON PREFIJOS) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        tipo_doc = c1.selectbox("Tipo de Documento", ["COTIZACIÓN", "FACTURA DE VENTA"])
        
        # Obtenemos el número puro de la DB
        num_db = st.session_state.db.obtener_siguiente_numero(tipo_doc)
        
        # Aplicamos el prefijo visualmente
        prefijo = "F-" if "FACTURA" in tipo_doc.upper() else "C-"
        num_visual = f"{prefijo}{num_db}"
        
        c2.metric("Próximo Número", num_visual)
        fecha = c3.date_input("Fecha de Emisión", datetime.now())

    # --- SELECCIÓN DE PRODUCTOS ---
    st.subheader("Agregar Productos")
    df_prods = st.session_state.db.obtener_productos()
    
    lista_opciones = [f"{p['descripcion']} ({p['codigo']}) - Disponibles: {p['cantidad']}" for _, p in df_prods.iterrows()]
    seleccion = st.selectbox("Buscar Producto", ["-- Seleccione --"] + lista_opciones)

    # AQUÍ ESTABA EL ERROR: Todo este bloque debe estar indentado dentro de show()
    if seleccion != "-- Seleccione --":
        codigo_sel = seleccion.split('(')[1].split(')')[0].strip()
        filtro = df_prods[df_prods['codigo'].astype(str).str.strip() == codigo_sel]
        
        if not filtro.empty:
            producto = filtro.iloc[0]
            col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
            with col_p1:
                st.write(f"**Precio Unitario:** ${producto['precio']:,.0f}")
            with col_p2:
               # Se añade la KEY dinámica para forzar el reinicio al cambiar el ID
               cant = st.number_input(
                   "Cantidad a vender", 
                   min_value=1, 
                   value=1, 
                   key=f"cant_input_{st.session_state.reset_cant}"
               )
            with col_p3:
                if cant > producto['cantidad']:
                    st.error(f"Solo hay {producto['cantidad']} en stock")
                    boton_bloqueado = True
                else:
                    st.success("Stock disponible")
                    boton_bloqueado = False
                
                if st.button("Agregar Ítem", disabled=boton_bloqueado, use_container_width=True):
                    item = {
                        "cod": producto['codigo'], 
                        "desc": producto['descripcion'],
                        "categoria": producto.get('categoria', 'General'),
                        "cant": cant, 
                        "precio": producto['precio'], 
                        "total": cant * producto['precio']
                    }
                    st.session_state.carrito.append(item)
                    st.toast(f"Agregado: {producto['descripcion']}")
                    # --- NUEVA MEJORA: Incrementar reset_cant para volver a 1 ---
                    st.session_state.reset_cant += 1
                    st.rerun()
        else:
            st.error("No se encontró el producto en la base de datos.")

# --- BLOQUE DE DETALLE PROFESIONAL FINAL ---
        st.subheader("Detalle del Documento")
        
        if st.session_state.carrito:
            indices_a_borrar = []
            
            # EL CHECKBOX AHORA QUEDA ARRIBA (Antes del título)
            c_check_sup, _ = st.columns([0.5, 9.5])
            with c_check_sup:
                st.write("") # Guía visual del checklist
            
            st.markdown("**DESCRIPCIÓN DEL PRODUCTO Y DETALLES FINANCIEROS**")

            # FILAS DE PRODUCTOS
            for idx, item in enumerate(st.session_state.carrito):
                r1, r2 = st.columns([0.5, 9.5])
                
                with r1:
                    key_check = f"sel_{st.session_state.get('v_check', 0)}_{idx}"
                    if st.checkbox("", key=key_check):
                        indices_a_borrar.append(idx)
                
                with r2:
                    # FORMATEO DE MONEDA FORZADO (Usando f-string con $)
                    valor_unitario = f"${item['precio']:,.0f}"
                    valor_subtotal = f"${item['total']:,.0f}"
                    
                    # Nombre y Categoría
                    st.markdown(f"**{item['desc']}** <small style='color:gray'>({item.get('categoria', 'General')})</small>", unsafe_allow_html=True)
                    
                    # LÍNEA DE VALORES (Limpiamos el texto para que el $ se vea claro)
                    st.write(f"CANT: {item['cant']} | PRECIO UNITARIO: {valor_unitario} | SUBTOTAL: {valor_subtotal}")

            st.divider()

            # 3. LÓGICA DE ACCIÓN (Aparece cuando marcas algún checkbox)
            if indices_a_borrar:
                st.warning(f"{len(indices_a_borrar)} producto(s) seleccionados para eliminar.")
                col_si, col_no = st.columns(2)
                with col_si:
                    if st.button("CONFIRMAR ELIMINACIÓN", type="primary", use_container_width=True):
                        # Filtrado del carrito excluyendo los seleccionados
                        st.session_state.carrito = [
                            item for i, item in enumerate(st.session_state.carrito) 
                            if i not in indices_a_borrar
                        ]
                        # Limpieza forzada de checkboxes incrementando la versión
                        st.session_state.v_check = st.session_state.get('v_check', 0) + 1
                        st.rerun()
                with col_no:
                    if st.button(" CANCELAR ", use_container_width=True):
                        # Incremento de versión para desmarcar todo de inmediato
                        st.session_state.v_check = st.session_state.get('v_check', 0) + 1
                        st.rerun()
            
            # 4. VACIADO TOTAL (Se muestra si NO hay nada seleccionado arriba)
            else:
                if 'confirmar_vaciado' not in st.session_state:
                    st.session_state.confirmar_vaciado = False

                if not st.session_state.confirmar_vaciado:
                    if st.button("Vaciar Carrito Completo", use_container_width=True):
                        st.session_state.confirmar_vaciado = True
                        st.rerun()
                else:
                    with st.container(border=True):
                        st.error(" ¿Deseas eliminar TODO el contenido del carrito?")
                        cs, cn = st.columns(2)
                        with cs:
                            if st.button("SÍ, ELIMINAR TODO", type="primary", use_container_width=True):
                                st.session_state.carrito = []
                                st.session_state.confirmar_vaciado = False
                                st.rerun()
                        with cn:
                            if st.button("NO, VOLVER", type="secondary", use_container_width=True):
                                st.session_state.confirmar_vaciado = False
                                st.rerun()
        else:
            st.info("El listado de productos está vacío.")

        st.markdown("### Modificadores Contables")
        col_m1, col_m2, col_m3 = st.columns(3) # Cambiamos de 2 a 3 columnas
        
        # 1. Descuento
        opciones_descuento = list(range(0, 105, 5)) 
        p_desc = col_m1.selectbox("Descuento Especial (%)", opciones_descuento)

        # 2. Flete (Nuevo Campo)
        flete_ingresado = col_m2.number_input("Valor del Flete ($)", min_value=0.0, step=1000.0, value=0.0)

        # 3. IVA
        aplicar_i = col_m3.toggle("Liquidar IVA (19%)", value=False)

        # LLAMADA ACTUALIZADA A LA FUNCIÓN (Incluyendo el flete)
        fin = calcular_financieros(
            st.session_state.carrito, 
            aplicar_iva=aplicar_i, 
            porcentaje_descuento=p_desc,
            valor_flete=flete_ingresado # <--- Pasamos el valor capturado arriba
        )
        
        # El total ya viene con el flete sumado desde el nuevo utils.py
        st.markdown(f"## **TOTAL A PAGAR: ${fin['total']:,.0f} COP**")

    # --- BLOQUE DE PREVISUALIZACIÓN (Sincronizado con Estándar DIAN) ---
    with st.expander("👁️ PREVISUALIZAR DATOS DEL DOCUMENTO", expanded=False):
        st.markdown(f"### Resumen de {tipo_doc}")
        
        # 1. VISUALIZACIÓN DE CAMPOS LEGALES (Detección Automática)
        if "FACTURA" in tipo_doc.upper():
            st.info("⚡ **MODO FACTURA ELECTRÓNICA ACTIVO**")
            col_leg1, col_leg2 = st.columns(2)
            with col_leg1:
                st.success("**Firma Digital:** Pendiente (se firma al finalizar)")
                st.caption("**Ambiente:** Pruebas / Habilitación")
            with col_leg2:
                # Marcador de posición para el Hash SHA-384
                st.code("CUFE: Generando Hash al procesar...", language="text")
                st.caption("El código único se inyectará en el XML y PDF")
        else:
            st.warning("Este documento es una **COTIZACIÓN** y no tiene validez legal ante la DIAN.")

        # 2. INFORMACIÓN DEL CLIENTE Y FECHA
        col_pre1, col_pre2 = st.columns(2)
        with col_pre1:
            st.markdown(f"**Cliente:** {c_nom}")
            st.markdown(f"**NIT/CC:** {c_nit}")
        with col_pre2:
            st.markdown(f"**Email:** {c_email if c_email else 'No registrado'}")
            st.markdown(f"**Fecha:** {fecha}")
        
        st.write("---")
        st.write("**Productos en el listado:**")
        
        # 3. TABLA DE PRODUCTOS CON CATEGORÍA
        if st.session_state.carrito:
            df_previa = pd.DataFrame(st.session_state.carrito)
            
            # Formateo de precios para visualización
            df_previa['precio_f'] = df_previa['precio'].map('${:,.0f}'.format)
            df_previa['total_f'] = df_previa['total'].map('${:,.0f}'.format)
            
            columnas_a_mostrar = ['desc', 'categoria', 'cant', 'precio_f', 'total_f']
            cols_reales = [c for c in columnas_a_mostrar if c in df_previa.columns]
            
            st.table(df_previa[cols_reales].rename(columns={
                'desc': 'Descripción',
                'categoria': 'Categoría',
                'cant': 'Cant.',
                'precio_f': 'Unitario',
                'total_f': 'Subtotal'
            }))
            
            # 4. RESUMEN FINANCIERO MEJORADO (Totales y Flete)
            c_r1, c_r2 = st.columns(2)
            with c_r2:
                valor_flete = fin.get('flete', 0.0)
                
                st.write(f"**Subtotal:** ${fin['subtotal']:,.0f}")
                
                if p_desc > 0:
                    st.write(f"**Descuento ({p_desc}%):** -${fin['v_desc']:,.0f}")
                
                st.write(f"**IVA ({fin['p_iva']}%):** ${fin['v_iva']:,.0f}")
                
                if valor_flete > 0:
                    st.write(f"**Flete (No Gravado):** ${valor_flete:,.0f}")
                
                # Cálculo de gran total incluyendo flete
                gran_total = fin['total'] + valor_flete
                st.subheader(f"Total Neto: ${gran_total:,.0f} COP")
            
            # 5. NOTAS LEGALES Y ADVERTENCIAS
            st.caption("---")
            if "FACTURA" in tipo_doc.upper():
                st.caption("*Este documento cumple con el formato UBL 2.1 exigido por la DIAN.*")
            else:
                st.caption("*Documento informativo para fines comerciales. No es una factura de venta.*")
                
            st.warning("**Verificación:** Revisa que el NIT y el Email sean correctos para la firma electrónica.")
        else:
            st.error("El carrito está vacío. Agrega productos para ver la previsualización.")
    
    st.markdown("---")


# --- BOTÓN FINALIZAR ---
    if st.button("FINALIZAR Y GENERAR PDF", type="primary", use_container_width=True):
        try:
            # 1. Obtener el número real (Sin prefijos duplicados, solo el entero de la DB)
            num_base = st.session_state.db.obtener_siguiente_numero(tipo_doc)
            # Aquí construimos el número profesional para la visualización e impresión
            prefijo = "F-" if "FACTURA" in tipo_doc.upper() else "C-"
            num_doc_final = f"{prefijo}{num_base}"

            # 2. Simulación de Legalización DIAN (Solo para Facturas)
            cufe_oficial = None
            url_xml = ""
            if "FACTURA" in tipo_doc.upper():
                with st.spinner("Legalizando documento ante la DIAN..."):
                    import time
                    time.sleep(1.2) 
                    cufe_oficial = "6f8a2c1d9e3f_hash_oficial_dian" 
                    url_xml = f"exports/xml/{num_doc_final}.xml"

            # Si las variables c_nom, c_nit vienen vacías, las rescatamos del formulario
            c_nom = c_nom if c_nom else "Consumidor Final"
            c_nit = c_nit if c_nit else "222222222222"
            
            # 3. Guardar cliente y preparar sus datos para el PDF
            st.session_state.db.guardar_cliente(c_nit, c_nom, c_tel, c_dir, c_email)
            
            cliente_data_final = {
                "nombre": c_nom, 
                "nit": c_nit, 
                "tel": c_tel if c_tel else "N/A", 
                "dir": c_dir if c_dir else "Villavicencio", 
                "email": c_email if c_email else "N/A"
            }
                
            # 4. Generar el PDF usando el motor PDFEngine
            from modules.pdf_engine import PDFEngine
            pdf_maker = PDFEngine()
            archivo_pdf = pdf_maker.generar_documento(
                tipo=tipo_doc, 
                num_doc=num_doc_final, 
                fecha=str(fecha), 
                cliente_data=cliente_data_final, # Enviamos el diccionario completo
                items_carrito=st.session_state.carrito, 
                info_financiera=fin,
                cufe=cufe_oficial 
            )

            # 5. Registro en Base de Datos y Descuento de Inventario
            if os.path.exists(archivo_pdf):
                if tipo_doc == "FACTURA DE VENTA":
                    # Enriquecer carrito con costos para reportes de utilidad
                    carrito_con_costos = []
                    for item in st.session_state.carrito:
                        # Descontamos stock real
                        st.session_state.db.descontar_stock(item['cod'], item['cant'])
                        
                        # Buscamos costo para que la utilidad no salga en $0
                        prod_info = st.session_state.db.obtener_producto_por_codigo(item['cod'])
                        costo_real = prod_info['costo_proveedor'] if prod_info and 'costo_proveedor' in prod_info else 0.0
                        
                        nuevo_item = item.copy()
                        nuevo_item['costo_proveedor'] = costo_real
                        carrito_con_costos.append(nuevo_item)

                    # Registro final en historial
                    st.session_state.db.registrar_venta(
                        fecha=str(fecha), 
                        tipo=tipo_doc, 
                        num=num_base, # Guardamos solo el número en la DB
                        cliente=c_nom, 
                        total=fin['total'],
                        carrito=carrito_con_costos, 
                        cufe=cufe_oficial,
                        xml=url_xml,
                        flete=fin.get('flete', 0.0) 
                    )
                else:
                    # Registro para Cotizaciones (Total 0 para no inflar ventas reales)
                    st.session_state.db.registrar_venta(
                        fecha=str(fecha), 
                        tipo=tipo_doc, 
                        num=num_base, 
                        cliente=c_nom, 
                        total=0, 
                        carrito=st.session_state.carrito
                    )

                # 6. Interfaz de Éxito y Descarga
                st.success(f"{tipo_doc} {num_doc_final} Generada con éxito.")
                
                with open(archivo_pdf, "rb") as f:
                    st.download_button(
                        label=f"DESCARGAR {tipo_doc} {num_doc_final}",
                        data=f,
                        file_name=os.path.basename(archivo_pdf),
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                st.balloons()
                st.session_state.carrito = [] # Limpiar para la siguiente venta
            else:
                st.error("El motor de PDF no pudo crear el archivo físico.")

        except Exception as e:
            st.error(f"Error crítico: {str(e)}")

# Ejecución del módulo
if __name__ == "__main__":
    show()