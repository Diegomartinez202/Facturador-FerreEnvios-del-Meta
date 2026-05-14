import re

def calcular_financieros(items, tasa_iva=19, aplicar_iva=True, porcentaje_descuento=0):
    """Calcula la liquidación total con IVA y Descuento"""
    # Suma de todos los items en el carrito
    bruto_sin_nada = sum(item['total'] for item in items)
    
    # 1. Aplicar Descuento Comercial
    valor_descuento = bruto_sin_nada * (porcentaje_descuento / 100)
    base_después_desc = bruto_sin_nada - valor_descuento
    
    # 2. Manejo de IVA (sobre la base ya descontada)
    if aplicar_iva:
        subtotal = base_después_desc / (1 + (tasa_iva / 100))
        valor_iva = base_después_desc - subtotal
    else:
        subtotal = base_después_desc
        valor_iva = 0
        tasa_iva = 0

    return {
        "bruto": bruto_sin_nada,
        "v_desc": valor_descuento,
        "p_desc": porcentaje_descuento,
        "subtotal": subtotal,
        "p_iva": tasa_iva,
        "v_iva": valor_iva,
        "total": base_después_desc
    }

def formatear_codigo(codigo_raw):
    """Limpia códigos que vengan con espacios o puntos del PDF"""
    return str(codigo_raw).strip().replace('.0', '')