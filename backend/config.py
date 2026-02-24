import os

class Config:
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://gl313.com/api/')
    API_TOKEN = os.getenv('API_TOKEN', '')
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    VALHALLA_URL = os.getenv('VALHALLA_URL', 'http://localhost')
    VALHALLA_PORT = int(os.getenv('VALHALLA_PORT', '8002'))

