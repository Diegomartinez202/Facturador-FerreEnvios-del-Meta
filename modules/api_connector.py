import requests


class DIANConnector:
    def __init__(self, api_key):
        self.url_api = "https://api.proveedor.com/v1/factura"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def enviar_factura(self, datos_json):
        """
        Envía el JSON, el PT construye el XML, calcula el CUFE
        y nos devuelve la respuesta oficial.
        """
        try:
            response = requests.post(
                self.url_api, json=datos_json, headers=self.headers
            )
            if response.status_code == 201:
                res = response.json()
                return {
                    "exitoso": True,
                    "cufe": res["cufe"],
                    "url_xml": res["xml_path"],
                    "qr": res["qr_data"],
                }
            return {"exitoso": False, "error": response.text}
        except Exception as e:
            return {"exitoso": False, "error": str(e)}
