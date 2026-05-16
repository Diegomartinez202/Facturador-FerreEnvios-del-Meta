def calcular_financieros(
    items, tasa_iva=19, aplicar_iva=True, porcentaje_descuento=0, valor_flete=0.0
):
    """Calcula la liquidación total sumando el IVA y el Flete correctamente"""
    # Suma bruta de los productos (Ya traen IVA incluido)
    bruto_con_iva = sum(item["total"] for item in items)

    # 1. Aplicamos Descuento sobre el valor bruto
    valor_descuento = bruto_con_iva * (porcentaje_descuento / 100)
    # Valor de la mercancía después de descuento pero aún con IVA
    mercancia_neta_con_iva = bruto_con_iva - valor_descuento

    # 2. Desglose de Impuestos (DIAN: El IVA se calcula sobre el valor neto)
    if aplicar_iva:
        # Desglosamos el subtotal (Base Imponible)
        # Si mercancia_neta_con_iva es 54,569 -> subtotal es 45,856.3
        subtotal = mercancia_neta_con_iva / (1 + (tasa_iva / 100))
        valor_iva = mercancia_neta_con_iva - subtotal
    else:
        subtotal = mercancia_neta_con_iva
        valor_iva = 0
        tasa_iva = 0

    # 3. TOTAL FINAL (Mercancía neta + Flete)
    # 54,569 (Alicate con desc) + 3,000 (Flete) = 57,569
    total_neto = mercancia_neta_con_iva + valor_flete

    return {
        "bruto": bruto_con_iva,
        "v_desc": valor_descuento,
        "p_desc": porcentaje_descuento,
        "subtotal": round(subtotal, 2),  # Mantener decimales para el PDF
        "p_iva": tasa_iva,
        "v_iva": round(valor_iva, 2),  # Mantener decimales para el PDF
        "flete": valor_flete,
        "total": round(total_neto, 2),
    }


def formatear_codigo(codigo_raw):
    """Limpia códigos que vengan con espacios o decimales accidentales (.0)"""
    if codigo_raw is None:
        return ""
    # Convierte a string, quita espacios y el .0 si es un float de Excel
    return str(codigo_raw).strip().replace(".0", "")
