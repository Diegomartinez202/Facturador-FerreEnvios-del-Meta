import qrcode
import os
import hashlib
from config import EMISOR


class LegalLogic:
    @staticmethod
    def generar_cufe(
        num_fac,
        fecha,
        hora,
        valor_fac,
        nit_emisor,
        doc_adqui,
        clave_tecnica,
        ambiente="1",
    ):
        """
        Genera el Hash SHA-384 oficial exigido por la DIAN.
        """
        # Formato de cadena técnica según Anexo 1.8 de la DIAN
        cadena_corta = f"{num_fac}{fecha}{hora}{valor_fac}010.00020.00030.00{valor_fac}{nit_emisor}{doc_adqui}{clave_tecnica}{ ambiente}"

        # Aplicamos SHA-384
        cufe = hashlib.sha384(cadena_corta.encode()).hexdigest()
        return cufe

    @staticmethod
    def generar_qr_dian(tipo, num_doc, cufe, total):
        """
        Genera un QR oficial. Si hay CUFE, apunta a la validación de la DIAN.
        """
        folder_qr = "assets/qrs"
        if not os.path.exists(folder_qr):
            os.makedirs(folder_qr)

        if cufe:
            # Estructura oficial para el validador de la DIAN
            contenido = (
                f"NumFac: {num_doc}\n"
                f"NitFac: {EMISOR['nit']}\n"
                f"ValFac: {total}\n"
                f"CUFE: {cufe}\n"
                f"URL: https://catalogo-vpfe.dian.gov.co/document/searchqr?documentKey={cufe}"
            )
        else:
            contenido = (
                f"Documento: {tipo} No: {num_doc}\nTotal: {total}\nFerreEnvios del Meta"
            )

        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(contenido)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1A365D", back_color="white")
        path_qr = f"{folder_qr}/qr_{num_doc}.png"
        img.save(path_qr)
        return path_qr
