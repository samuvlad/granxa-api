import json
from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from shapely.ops import transform
import pyproj


def geojson_to_geometry(geojson: dict[str, Any]) -> Any:
    """Converte un GeoJSON (Feature ou geometry) nun obxecto GeoAlchemy2 Geometry."""
    if geojson.get("type") == "Feature":
        geom = geojson["geometry"]
    else:
        geom = geojson
    shp = shape(geom)
    return from_shape(shp, srid=4326)


def geometry_to_geojson(geometry: Any) -> dict[str, Any]:
    """Converte un obxecto GeoAlchemy2 Geometry a un GeoJSON geometry dict."""
    shp = to_shape(geometry)
    return mapping(shp)


def calculate_area_m2(geometry: Any) -> float:
    """Calcula a área en metros cadrados proxectando a UTM adecuada."""
    shp = to_shape(geometry)
    centroid = shp.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "north" if centroid.y >= 0 else "south"
    crs = f"EPSG:326{utm_zone:02d}" if hemisphere == "north" else f"EPSG:327{utm_zone:02d}"

    project = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    projected = transform(project, shp)
    return projected.area


def calculate_perimeter_m(geometry: Any) -> float:
    """Calcula o perímetro en metros proxectando a UTM adecuada."""
    shp = to_shape(geometry)
    centroid = shp.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "north" if centroid.y >= 0 else "south"
    crs = f"EPSG:326{utm_zone:02d}" if hemisphere == "north" else f"EPSG:327{utm_zone:02d}"

    project = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    projected = transform(project, shp)
    return projected.length
