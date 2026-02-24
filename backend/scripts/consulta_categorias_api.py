import os
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "https://gl313.com/api/")
API_TOKEN = os.environ.get("API_TOKEN", "<TOKEN_AQUI>")

HEADERS = {"Authorization": f"Token {API_TOKEN}"}


def get_categorias(parent=None, parent_isnull=None, nome=None, search=None):
    """
    Consulta a API REST para obter categorías, con filtros opcionais.
    """
    url = f"{API_BASE_URL}taxonomia/categorias/"
    params = {}
    if parent is not None:
        params["parent"] = parent
    if parent_isnull is not None:
        params["parent_isnull"] = str(parent_isnull).lower()
    if nome:
        params["nome__icontains"] = nome
    if search:
        params["search"] = search
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_categoria_detalle(slug):
    """
    Consulta o detalle dunha categoría polo seu slug.
    """
    url = f"{API_BASE_URL}taxonomia/categorias/{slug}/"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()

def busca_slug_categoria_ruta(nomes):
    """
    Busca recursivamente o slug dunha ruta de categorías, ex: ["Servizos", "Hostalaría", "Aloxamento"]
    """
    # Eliminado soporte para aloxamento
    if [n.lower() for n in nomes] == ["servizos", "hostalaría", "aloxamento"]:
        return None
    parent = None
    slug = None
    for nome in nomes:
        data = get_categorias(parent=parent) if parent else get_categorias()
        match = next((c for c in data.get("results", []) if c["nome"].lower() == nome.lower()), None)
        if not match:
            print(f"Non se atopa a categoría '{nome}' baixo parent={parent}")
            return None
        slug = match["slug"]
        parent = match["id"]
    return slug

if __name__ == "__main__":
    # Exemplo: buscar slug de "Servizos → Hostalaría → Aloxamento"
    ruta = ["Servizos", "Hostalaría", "Aloxamento"]
    slug = busca_slug_categoria_ruta(ruta)
    if slug:
        print(f"Slug para {' → '.join(ruta)}: {slug}")
        detalle = get_categoria_detalle(slug)
        print("Detalle da categoría:")
        print(detalle)
    else:
        print("Non se atopou a ruta completa de categorías.")
