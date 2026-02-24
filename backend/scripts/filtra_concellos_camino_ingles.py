import geopandas as gpd
from shapely.geometry import shape
import os

# Paths
BASE = os.path.dirname(os.path.dirname(__file__))
geojson_dir = os.path.join(BASE, 'static', 'geojson')
camino_path = os.path.join(geojson_dir, 'camino_ingles.geojson')
concellos_path = os.path.join(geojson_dir, 'concellos_camino.geojson')
output_path = os.path.join(geojson_dir, 'concellos_camino_ingles.geojson')

# Load GeoJSONs
gdf_camino = gpd.read_file(camino_path)
gdf_concellos = gpd.read_file(concellos_path)

# Unify camiño geometry (MultiLineString)
camino_geom = gdf_camino.unary_union

# Filter concellos intersecting camiño
gdf_concellos_camino = gdf_concellos[gdf_concellos.intersects(camino_geom)]

# Save result
gdf_concellos_camino.to_file(output_path, driver='GeoJSON')
print(f"Concellos do camiño inglés gardados en: {output_path}")
