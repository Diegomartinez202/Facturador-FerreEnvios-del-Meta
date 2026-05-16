import requests
import streamlit as st


class ClienteApiSiigo:
    def __init__(self, username, access_key, es_produccion=False):
        # URLs oficiales de Siigo API V1
        self.base_url = "https://api.siigo.com/v1"
        self.username = username
        self.access_key = access_key
        self.token = None

    def autenticar(self):
        """Obtiene el Token JWT. Siigo exige Username (email) y Access Key."""
        url = f"{self.base_url}/auth"
        payload = {"username": self.username, "access_key": self.access_key}
        headers = {"Content-Type": "application/json"}

        try:
            # Agregamos un st.spinner si se llama desde la interfaz
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                self.token = res.json().get("access_token")
                return True
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"Error de conexión con Siigo: {e}")
            return False

    def enviar_factura(self, payload_factura):
        """
        Envía el JSON de la factura al endpoint de Siigo.
        El payload debe cumplir con el estándar UBL 2.1 que pide Siigo.
        """
        if not self.token:
            if not self.autenticar():
                return {"error": "Fallo de autenticación"}, 401

        url = f"{self.base_url}/invoices"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Partner-Id": "FerreEnviosMeta",  # Identificador opcional
        }

        try:
            res = requests.post(url, json=payload_factura, headers=headers, timeout=20)
            return res.json(), res.status_code
        except Exception as e:
            return {"error": str(e)}, 500
        
    def es_api_de_prueba(self):
        """Verifica si las credenciales corresponden al modo de desarrollo"""
        return self.username == "TEST_MODE" or self.username == "dummy"
