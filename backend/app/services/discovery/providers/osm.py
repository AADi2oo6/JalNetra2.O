import json
import logging
import math
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.services.discovery.base import WaterBodyProvider
from app.services.discovery.models import WaterBodyDiscoveryResult, compute_geometry_hash_from_dict

logger = logging.getLogger("jalnetra.discovery.osm")

# Canonical water body categories and keywords in OpenStreetMap
WATER_BODY_KEYWORDS = {
    "water",
    "lake",
    "reservoir",
    "river",
    "stream",
    "canal",
    "lagoon",
    "pond",
    "wetland",
    "basin",
    "bay",
    "strait",
    "oxbow",
}

WATER_CLASSES = {"natural", "waterway", "landuse"}


class OpenStreetMapProvider(WaterBodyProvider):
    """
    OpenStreetMap provider leveraging the public Nominatim API with polygon GeoJSON output.
    Follows OSM Nominatim Usage Policy:
    - Custom descriptive User-Agent with contact/app identity
    - Strict query timeouts
    - Structured query parameters
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self._user_agent = user_agent or settings.WATERBODY_DISCOVERY_USER_AGENT
        self._timeout = timeout_seconds or settings.WATERBODY_DISCOVERY_TIMEOUT_SECONDS
        self._base_url = base_url or self.NOMINATIM_URL
        self._client = client

    @property
    def name(self) -> str:
        return "osm"

    @property
    def description(self) -> str:
        return "OpenStreetMap Nominatim Geographic Search Engine"

    async def check_health(self) -> bool:
        # Static availability check based on configuration
        return settings.WATERBODY_DISCOVERY_ENABLED

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[WaterBodyDiscoveryResult]:
        query = query.strip()
        if not query:
            return []

        limit = min(max(1, limit), 20)

        params: Dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "polygon_geojson": 1,
            "addressdetails": 1,
            "extratags": 1,
            "limit": limit,
        }

        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }

        try:
            if self._client:
                response = await self._client.get(
                    self._base_url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        self._base_url,
                        params=params,
                        headers=headers,
                    )

            if response.status_code >= 400:
                logger.warning(
                    "OSM Nominatim returned HTTP %s for query '%s'",
                    response.status_code,
                    query,
                )
                return []

            data = response.json()
            if not isinstance(data, list):
                logger.warning("OSM Nominatim unexpected response format: %s", type(data))
                return []

            results: List[WaterBodyDiscoveryResult] = []
            for item in data:
                normalized = self._normalize_item(item)
                if normalized:
                    results.append(normalized)

            # Sort/prioritize actual water body types over generic geographic places
            results.sort(key=lambda r: (0 if self._is_water_feature(r) else 1))
            return results

        except httpx.TimeoutException:
            logger.warning("OSM Nominatim timeout after %ss for query '%s'", self._timeout, query)
            raise
        except httpx.RequestError as exc:
            logger.warning("OSM Nominatim network error: %s", exc)
            raise
        except Exception as exc:
            logger.error("OSM Nominatim unexpected exception: %s", exc, exc_info=True)
            raise

    def _is_water_feature(self, res: WaterBodyDiscoveryResult) -> bool:
        wb_type = (res.water_body_type or "").lower()
        if any(kw in wb_type for kw in WATER_BODY_KEYWORDS):
            return True
        name_lower = res.name.lower()
        if any(kw in name_lower for kw in WATER_BODY_KEYWORDS):
            return True
        return False

    def _normalize_item(self, item: Dict[str, Any]) -> Optional[WaterBodyDiscoveryResult]:
        try:
            osm_type = item.get("osm_type", "node")
            osm_id = item.get("osm_id", "")
            source_id = f"{osm_type}/{osm_id}" if osm_id else str(item.get("place_id", ""))

            # Name extraction
            name = item.get("name")
            display_name = item.get("display_name", "")
            if not name:
                name = display_name.split(",")[0].strip() if display_name else "Unknown Water Body"

            # Classification & water body type
            item_class = str(item.get("class", "")).lower()
            item_type = str(item.get("type", "")).lower()

            # Determine water body type
            water_body_type = None
            if item_type in WATER_BODY_KEYWORDS:
                water_body_type = item_type
            elif item_class in WATER_CLASSES and item_type:
                water_body_type = item_type
            elif any(kw in (name.lower()) for kw in WATER_BODY_KEYWORDS):
                for kw in WATER_BODY_KEYWORDS:
                    if kw in name.lower():
                        water_body_type = kw
                        break
            else:
                water_body_type = item_type or item_class or "water"

            # Address details
            address = item.get("address", {}) or {}
            country = address.get("country")
            state_province = address.get("state") or address.get("province") or address.get("region")
            district = address.get("state_district") or address.get("county") or address.get("district")
            city = address.get("city") or address.get("town") or address.get("municipality") or address.get("village")

            # Geometry parsing
            geom = item.get("geojson")
            geom_str = None
            geom_hash = None
            if geom and isinstance(geom, dict):
                geom_type = geom.get("type")
                if geom_type in ("Point", "Polygon", "MultiPolygon", "LineString", "MultiLineString"):
                    geom_str = json.dumps(geom)
                    geom_hash = compute_geometry_hash_from_dict(geom)

            # Bounding box [min_lat, max_lat, min_lon, max_lon] in Nominatim
            min_lat, max_lat, min_lon, max_lon = None, None, None, None
            bbox_raw = item.get("boundingbox")
            if bbox_raw and len(bbox_raw) == 4:
                try:
                    min_lat = float(bbox_raw[0])
                    max_lat = float(bbox_raw[1])
                    min_lon = float(bbox_raw[2])
                    max_lon = float(bbox_raw[3])
                except (ValueError, TypeError):
                    pass

            # Centroid
            centroid_lat, centroid_lon = None, None
            try:
                if "lat" in item and "lon" in item:
                    centroid_lat = float(item["lat"])
                    centroid_lon = float(item["lon"])
            except (ValueError, TypeError):
                pass

            # Calculate fallback bounds or centroid from each other if missing
            if centroid_lat is None and min_lat is not None and max_lat is not None:
                centroid_lat = (min_lat + max_lat) / 2.0
            if centroid_lon is None and min_lon is not None and max_lon is not None:
                centroid_lon = (min_lon + max_lon) / 2.0

            if min_lat is None and centroid_lat is not None:
                min_lat = max_lat = centroid_lat
            if min_lon is None and centroid_lon is not None:
                min_lon = max_lon = centroid_lon

            # Estimate approximate area in sq km if polygon bounding box is available
            area_sq_km = None
            if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
                d_lat = abs(max_lat - min_lat)
                d_lon = abs(max_lon - min_lon)
                if d_lat > 0 or d_lon > 0:
                    # Rough rectangular approximation at latitude: 1 deg lat ≈ 111 km, 1 deg lon ≈ 111 * cos(lat)
                    avg_lat_rad = math.radians(centroid_lat if centroid_lat is not None else min_lat)
                    km_lat = d_lat * 111.0
                    km_lon = d_lon * 111.0 * math.cos(avg_lat_rad)
                    area_sq_km = round(km_lat * km_lon, 3)

            return WaterBodyDiscoveryResult(
                provider="osm",
                source_id=source_id,
                name=name,
                water_body_type=water_body_type,
                country=country,
                state_province=state_province,
                district=district,
                city=city,
                description=display_name,
                geometry_geojson=geom_str,
                geometry_hash=geom_hash,
                min_lat=min_lat,
                min_lon=min_lon,
                max_lat=max_lat,
                max_lon=max_lon,
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
                area_sq_km=area_sq_km,
                source_metadata={
                    "osm_type": osm_type,
                    "osm_id": osm_id,
                    "place_id": item.get("place_id"),
                    "class": item_class,
                    "type": item_type,
                    "importance": item.get("importance"),
                },
            )
        except Exception as exc:
            logger.warning("Failed to normalize OSM item %s: %s", item.get("place_id"), exc)
            return None
