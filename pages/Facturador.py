import streamlit as st
import pandas as pd
from datetime import datetime
import os
from modules.pdf_engine import PDFEngine
from modules.utils import calcular_financieros

def show():
    # --- SEGURO DE CONEXIÓN A BASE DE DATOS ---
    if 'db' not in st.session_state:
        from modules.database_manager import DatabaseManager
        st.session_state.db = DatabaseManager()
    
    st.header("📝 Generador de Facturas y Cotizaciones")

    # Inicializar el carrito en la sesión si no existe
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

# --- NUEVA MEJORA: Estado para reiniciar cantidad ---
    if "reset_cant" not in st.session_state:
        st.session_state.reset_cant = 0
        
    # --- SECCIÓN DE CLIENTE ---
    st.subheader("👤 Información del Cliente")
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
    
    # --- CONFIGURACIÓN DEL DOCUMENTO ---
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        tipo_doc = c1.selectbox("Tipo de Documento", ["COTIZACIÓN", "FACTURA DE VENTA"])
        
        num_proximo = st.session_state.db.obtener_siguiente_numero(tipo_doc)
        c2.metric("Próximo Número", f"#{num_proximo}")
        
        fecha = c3.date_input("Fecha de Emisión", datetime.now())

    # --- SELECCIÓN DE PRODUCTOS ---
    st.subheader("📦 Agregar Productos")
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
                    st.error(f"⚠️ Solo hay {producto['cantidad']} en stock")
                    boton_bloqueado = True
                else:
                    st.success("✅ Stock disponible")
                    boton_bloqueado = False
                
                if st.button("📥 Agregar Ítem", disabled=boton_bloqueado, use_container_width=True):
                    item = {
                        "cod": producto['codigo'], 
                        "desc": producto['descripcion'],
                        "cant": cant, 
                        "precio": producto['precio'], 
                        "total": cant * producto['precio']
                    }
                    st.session_state.carrito.append(item)
                    st.toast("Producto agregado")
                    # --- NUEVA MEJORA: Incrementar reset_cant para volver a 1 ---
                    st.session_state.reset_cant += 1
                    st.rerun()
        else:
            st.error("No se encontró el producto en la base de datos.")

    # --- TABLA DE RESUMEN Y MODIFICADORES ---
    if st.session_state.carrito:
        st.markdown("---")
        st.subheader("📋 Detalle del Documento")
        
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 0.5])
            r1.write(f"**{item['desc']}**")
            r2.write(f"Cant: {item['cant']}")
            r3.write(f"${item['precio']:,.0f}")
            r4.write(f"**${item['total']:,.0f}**")
            if r5.button("🗑️", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.markdown("### 🎛️ Modificadores Contables")
        col_m1, col_m2 = st.columns(2)
        # Escala de 5 en 5 hasta 100
        opciones_descuento = list(range(0, 105, 5)) 
        p_desc = col_m1.selectbox("Aplicar Descuento Especial (%)", opciones_descuento)

        # IVA desactivado por defecto (value=False)
        aplicar_i = col_m2.toggle("Liquidar IVA (19%)", value=False)

        fin = calcular_financieros(st.session_state.carrito, aplicar_iva=aplicar_i, porcentaje_descuento=p_desc)
        st.markdown(f"## **TOTAL A PAGAR: ${fin['total']:,.0f} COP**")

    # --- BLOQUE DE PREVISUALIZACIÓN (MEJORADO) ---
    with st.expander("👁️ PREVISUALIZAR DATOS DEL DOCUMENTO", expanded=False):
        st.markdown(f"### Resumen de {tipo_doc}")
        col_pre1, col_pre2 = st.columns(2)
        with col_pre1:
            st.markdown(f"**Cliente:** {c_nom}")
            st.markdown(f"**NIT/CC:** {c_nit}")
        with col_pre2:
            st.markdown(f"**Email:** {c_email if c_email else 'No registrado'}")
            st.markdown(f"**Fecha:** {fecha}")
        
        st.write("---")
        st.write("**📦 Productos en el listado:**")
        
        # Validación para que no se rompa si el carrito está vacío
        if st.session_state.carrito:
            df_previa = pd.DataFrame(st.session_state.carrito)
            # Formateamos los números en la tabla para que se vean bien
            df_previa['precio'] = df_previa['precio'].map('${:,.0f}'.format)
            df_previa['total'] = df_previa['total'].map('${:,.0f}'.format)
            
            st.table(df_previa[['desc', 'cant', 'precio', 'total']]) 
            
            # --- MEJORA: Resumen financiero dentro de la previa ---
            c_r1, c_r2 = st.columns(2)
            with c_r2:
                st.write(f"**Subtotal:** ${fin['subtotal']:,.0f}")
                st.write(f"**Descuento ({p_desc}%):** -${fin['v_desc']:,.0f}")
                st.write(f"**IVA ({fin['p_iva']}%):** ${fin['v_iva']:,.0f}")
                st.subheader(f"Total: ${fin['total']:,.0f}")
            
            st.warning("⚠️ Revisa que la información sea correcta antes de procesar la firma del documento.")
        else:
            st.error("🚫 El carrito está vacío. Agrega productos para ver la previsualización.")
    
    st.markdown("---")

    # --- BOTÓN FINALIZAR ---
    if st.button("🏁 FINALIZAR Y GENERAR PDF", type="primary", use_container_width=True):
        try:
            # A. Obtener el número real
            num_doc_final = st.session_state.db.obtener_siguiente_numero(tipo_doc)
                
            # B. Guardar cliente (Asegurando 5 campos)
            st.session_state.db.guardar_cliente(c_nit, c_nom, c_tel, c_dir, c_email)
            cliente_data_final = {"nombre": c_nom, "nit": c_nit, "tel": c_tel, "dir": c_dir, "email": c_email}
                
            # C. Generar el PDF PRIMERO (Para asegurar que el archivo existe antes de registrar)
            pdf_maker = PDFEngine()
            archivo_pdf = pdf_maker.generar_documento(
                tipo=tipo_doc, 
                num_doc=num_doc_final, 
                fecha=str(fecha), 
                cliente_data=cliente_data_final, 
                items_carrito=st.session_state.carrito, 
                info_financiera=fin
             )

            # D. Solo si el PDF se creó con éxito, registramos en la DB y descontamos stock
            if os.path.exists(archivo_pdf):
                if tipo_doc == "FACTURA DE VENTA":
                    for item in st.session_state.carrito:
                        st.session_state.db.descontar_stock(item['cod'], item['cant'])
                    st.session_state.db.registrar_venta(str(fecha), tipo_doc, num_doc_final, c_nom, fin['total'])
                else:
                    st.session_state.db.registrar_venta(str(fecha), tipo_doc, num_doc_final, c_nom, 0)

                # E. MOSTRAR RESULTADOS (Sin st.rerun inmediato para no borrar el botón de descarga)
                st.success(f"✅ {tipo_doc} #{num_doc_final} Generada con éxito.")
                    
                with open(archivo_pdf, "rb") as f:
                    st.download_button(
                        label=f"🚀 DESCARGAR {tipo_doc} #{num_doc_final}",
                        data=f,
                        file_name=os.path.basename(archivo_pdf),
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_descarga_final"
                    )
                    
                st.balloons()
                # IMPORTANTE: No usamos st.rerun() aquí porque borraría el botón de descarga 
                # antes de que puedas hacer click. El carrito se limpia manualmente:
                st.session_state.carrito = []
            else:
                st.error("❌ El motor de PDF no pudo crear el archivo físico.")

        except Exception as e:
            st.error(f"💥 Error crítico en el proceso: {str(e)}")

# Ejecución
if __name__ == "__main__":
    show()