def calcular_financieros(items, tasa_iva=19, aplicar_iva=True, porcentaje_descuento=0, valor_flete=0.0):
    """Calcula la liquidación total sumando el IVA y el Flete correctamente"""
    # Suma base de los productos
    bruto_sin_nada = sum(item['total'] for item in items)
    
    # 1. Descuento
    valor_descuento = bruto_sin_nada * (porcentaje_descuento / 100)
    base_comercial = bruto_sin_nada - valor_descuento
    
    # 2. Lógica de Impuestos (Precio + IVA)
    if aplicar_iva:
        # En FerreEnvios el precio ya tiene el IVA, entonces lo desglosamos:
        subtotal = base_comercial / (1 + (tasa_iva / 100))
        valor_iva = base_comercial - subtotal
        # El neto de la mercancía sigue siendo base_comercial
    else:
        subtotal = base_comercial
        valor_iva = 0
        tasa_iva = 0

    # 3. TOTAL FINAL (Mercancía con IVA incluido + Flete)
    # Aquí estaba el error: Debe sumar la base comercial y el flete
    total_neto = base_comercial + valor_flete

    return {
        "bruto": bruto_sin_nada,
        "v_desc": valor_descuento,
        "p_desc": porcentaje_descuento,
        "subtotal": subtotal,
        "p_iva": tasa_iva,
        "v_iva": valor_iva,
        "flete": valor_flete,
        "total": total_neto 
    }
    
def formatear_codigo(codigo_raw):
    """Limpia códigos que vengan con espacios o decimales accidentales (.0)"""
    if codigo_raw is None:
        return ""
    # Convierte a string, quita espacios y el .0 si es un float de Excel
    return str(codigo_raw).strip().replace('.0', '')