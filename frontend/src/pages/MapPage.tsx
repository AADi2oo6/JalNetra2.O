import React, { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  ImageOverlay,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import {
  getWaterBodiesGeoJson,
  getMapScenes,
  getSceneRasterMetadata,
  getSceneRGBVisualization,
  getSceneRGBImageUrl,
  MapSceneItem,
  SceneRasterMetadata,
  RGBVisualizationData,
} from '../api/client';

// Component to dynamically fit map bounds
interface FitBoundsHelperProps {
  bounds: L.LatLngBoundsExpression | null;
}

const FitBoundsHelper: React.FC<FitBoundsHelperProps> = ({ bounds }) => {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
    }
  }, [bounds, map]);
  return null;
};

export const MapPage: React.FC = () => {
  // Vector data
  const [geoJsonData, setGeoJsonData] = useState<any | null>(null);
  const [selectedWaterBodyId, setSelectedWaterBodyId] = useState<string>('');
  const [selectedWaterBodyProps, setSelectedWaterBodyProps] = useState<any | null>(null);

  // Scenes
  const [scenes, setScenes] = useState<MapSceneItem[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string>('');
  const [selectedSceneItem, setSelectedSceneItem] = useState<MapSceneItem | null>(null);
  const [sceneMetadata, setSceneMetadata] = useState<SceneRasterMetadata | null>(null);

  // RGB Visualization
  const [rgbData, setRgbData] = useState<RGBVisualizationData | null>(null);
  const [isRenderingRgb, setIsRenderingRgb] = useState(false);
  const [rgbError, setRgbError] = useState<string | null>(null);

  // Layer Controls
  const [showBaseMap, setShowBaseMap] = useState(true);
  const [showWaterBodies, setShowWaterBodies] = useState(true);
  const [showSceneFootprint, setShowSceneFootprint] = useState(true);
  const [showRgbImagery, setShowRgbImagery] = useState(true);
  const [rasterOpacity, setRasterOpacity] = useState(0.85);

  // Camera Bounds
  const [targetBounds, setTargetBounds] = useState<L.LatLngBoundsExpression | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load Water Bodies GeoJSON on mount
  useEffect(() => {
    loadWaterBodies();
  }, []);

  const loadWaterBodies = async () => {
    setError(null);
    try {
      const data = await getWaterBodiesGeoJson();
      setGeoJsonData(data);
      // Auto-select first water body if available
      if (data?.features?.length > 0) {
        handleSelectWaterBody(data.features[0].properties.id, data.features[0].properties);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load water body map data');
    }
  };

  const handleSelectWaterBody = async (wbId: string, props?: any) => {
    setSelectedWaterBodyId(wbId);
    setSelectedSceneId('');
    setSelectedSceneItem(null);
    setSceneMetadata(null);
    setRgbData(null);
    setRgbError(null);

    // Find props if not provided
    const matchedFeature = geoJsonData?.features?.find((f: any) => f.properties.id === wbId);
    const properties = props || matchedFeature?.properties;
    setSelectedWaterBodyProps(properties);

    // Zoom to water body bounds
    if (properties?.bbox) {
      const [w, s, e, n] = properties.bbox;
      setTargetBounds([
        [s, w],
        [n, e],
      ]);
    } else if (properties?.centroid_lat && properties?.centroid_lon) {
      setTargetBounds([
        [properties.centroid_lat - 0.1, properties.centroid_lon - 0.1],
        [properties.centroid_lat + 0.1, properties.centroid_lon + 0.1],
      ]);
    }

    // Load registered satellite scenes for this water body
    try {
      const sceneList = await getMapScenes(wbId);
      setScenes(sceneList);
      if (sceneList.length > 0) {
        handleSelectScene(sceneList[0]);
      }
    } catch (err) {
      console.error('Failed to load scenes:', err);
    }
  };

  const handleSelectScene = async (sceneItem: MapSceneItem) => {
    setSelectedSceneId(sceneItem.scene_id);
    setSelectedSceneItem(sceneItem);
    setRgbData(null);
    setRgbError(null);

    // Zoom to scene footprint if available
    if (sceneItem.bbox) {
      const [w, s, e, n] = sceneItem.bbox;
      setTargetBounds([
        [s, w],
        [n, e],
      ]);
    }

    // Fetch raster metadata
    try {
      const meta = await getSceneRasterMetadata(sceneItem.scene_id);
      setSceneMetadata(meta);

      // If RGB bands are available, automatically load/render RGB
      if (meta.rgb_available || meta.rgb_cached) {
        loadRGBVisualization(sceneItem.scene_id);
      }
    } catch (err: any) {
      console.warn('Failed to load scene raster metadata:', err);
    }
  };

  const loadRGBVisualization = async (sceneId: string, force = false) => {
    setIsRenderingRgb(true);
    setRgbError(null);
    try {
      const data = await getSceneRGBVisualization(sceneId, force);
      setRgbData(data);
      // Zoom to raster bounds
      if (data.bounds) {
        setTargetBounds([
          [data.bounds.south, data.bounds.west],
          [data.bounds.north, data.bounds.east],
        ]);
      }
    } catch (err: any) {
      setRgbError(err.message || 'Failed to render RGB imagery');
    } finally {
      setIsRenderingRgb(false);
    }
  };

  // Convert GeoBounds to Leaflet LatLngBoundsExpression
  const rasterOverlayBounds: L.LatLngBoundsExpression | null = rgbData?.bounds
    ? [
        [rgbData.bounds.south, rgbData.bounds.west],
        [rgbData.bounds.north, rgbData.bounds.east],
      ]
    : null;

  return (
    <div style={styles.container}>
      {/* Top Banner */}
      <div style={styles.headerBanner}>
        <div>
          <h2 style={styles.headerTitle}>OPERATIONAL MONITORING MAP & SATELLITE VISUALIZATION</h2>
          <p style={styles.headerSubtitle}>
            Interactive GIS viewer displaying tracked water bodies, Sentinel-2 footprints, and aligned L2A True-Color (B04/B03/B02) rasters.
          </p>
        </div>
        <div style={styles.statusBadge}>
          <span style={styles.statusDot}></span>
          <span>CRS: EPSG:4326 (WGS84)</span>
        </div>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {/* Main Map Workspace */}
      <div style={styles.workspace}>
        {/* Left Side: Controls & Selector Panel */}
        <div style={styles.sidebar}>
          {/* Layer Visibility Control */}
          <div style={styles.panelCard}>
            <div style={styles.panelTitle}>LAYER CONTROLS</div>
            <div style={styles.layerRow}>
              <label style={styles.layerLabel}>
                <input
                  type="checkbox"
                  checked={showBaseMap}
                  onChange={(e) => setShowBaseMap(e.target.checked)}
                />
                <span style={styles.layerText}>Base Map (OpenStreetMap)</span>
              </label>
            </div>
            <div style={styles.layerRow}>
              <label style={styles.layerLabel}>
                <input
                  type="checkbox"
                  checked={showWaterBodies}
                  onChange={(e) => setShowWaterBodies(e.target.checked)}
                />
                <span style={styles.layerText}>Water Body Boundaries</span>
              </label>
            </div>
            <div style={styles.layerRow}>
              <label style={styles.layerLabel}>
                <input
                  type="checkbox"
                  checked={showSceneFootprint}
                  onChange={(e) => setShowSceneFootprint(e.target.checked)}
                />
                <span style={styles.layerText}>Scene Footprint</span>
              </label>
            </div>
            <div style={styles.layerRow}>
              <label style={styles.layerLabel}>
                <input
                  type="checkbox"
                  checked={showRgbImagery}
                  onChange={(e) => setShowRgbImagery(e.target.checked)}
                />
                <span style={styles.layerText}>Sentinel-2 RGB Overlay</span>
              </label>
            </div>

            {/* Opacity Slider */}
            {showRgbImagery && (
              <div style={styles.sliderContainer}>
                <div style={styles.sliderHeader}>
                  <span>Raster Opacity</span>
                  <span style={styles.sliderValue}>{Math.round(rasterOpacity * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={rasterOpacity}
                  onChange={(e) => setRasterOpacity(parseFloat(e.target.value))}
                  style={styles.slider}
                />
              </div>
            )}
          </div>

          {/* Water Body Selector */}
          <div style={styles.panelCard}>
            <div style={styles.panelTitle}>SELECT WATER BODY</div>
            <select
              style={styles.select}
              value={selectedWaterBodyId}
              onChange={(e) => handleSelectWaterBody(e.target.value)}
            >
              {geoJsonData?.features?.map((f: any) => (
                <option key={f.properties.id} value={f.properties.id}>
                  {f.properties.name} {f.properties.country ? `(${f.properties.country})` : ''}
                </option>
              ))}
            </select>

            {selectedWaterBodyProps && (
              <div style={styles.metaBox}>
                <div style={styles.metaRow}>
                  <span style={styles.metaKey}>Type:</span>
                  <span>{selectedWaterBodyProps.water_body_type || 'Inland Water'}</span>
                </div>
                <div style={styles.metaRow}>
                  <span style={styles.metaKey}>Source:</span>
                  <span>{selectedWaterBodyProps.source}</span>
                </div>
                {selectedWaterBodyProps.area_sq_km && (
                  <div style={styles.metaRow}>
                    <span style={styles.metaKey}>Area:</span>
                    <span>{Number(selectedWaterBodyProps.area_sq_km).toFixed(2)} km²</span>
                  </div>
                )}
                <button
                  style={styles.fitBtn}
                  onClick={() => {
                    if (selectedWaterBodyProps.bbox) {
                      const [w, s, e, n] = selectedWaterBodyProps.bbox;
                      setTargetBounds([[s, w], [n, e]]);
                    }
                  }}
                >
                  ZOOM TO WATER BODY
                </button>
              </div>
            )}
          </div>

          {/* Satellite Scenes Selector */}
          <div style={styles.panelCard}>
            <div style={styles.panelTitle}>REGISTERED SENTINEL-2 SCENES ({scenes.length})</div>
            {scenes.length === 0 ? (
              <div style={styles.emptyNote}>
                No downloaded scenes registered yet. Visit the Sentinel-2 tab to acquire imagery.
              </div>
            ) : (
              <div style={styles.sceneList}>
                {scenes.map((sc) => {
                  const isSelected = sc.scene_id === selectedSceneId;
                  return (
                    <div
                      key={sc.scene_id}
                      onClick={() => handleSelectScene(sc)}
                      style={{
                        ...styles.sceneCard,
                        borderColor: isSelected ? 'var(--color-primary)' : 'var(--border-color)',
                        backgroundColor: isSelected ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
                      }}
                    >
                      <div style={styles.sceneHeader}>
                        <span style={styles.sceneIdText}>{sc.external_scene_id}</span>
                        <span style={sc.has_rgb ? styles.badgeSuccess : styles.badgeWarn}>
                          {sc.has_rgb ? 'RGB READY' : 'PARTIAL BANDS'}
                        </span>
                      </div>
                      <div style={styles.sceneMetaRow}>
                        <span>Date: {new Date(sc.sensing_start).toLocaleDateString()}</span>
                        <span>Cloud: {sc.cloud_cover_percent != null ? `${sc.cloud_cover_percent.toFixed(1)}%` : 'N/A'}</span>
                      </div>
                      <div style={styles.sceneMetaRow}>
                        <span>Assets: {sc.downloaded_assets.join(', ') || 'none'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Raster Processing Actions */}
          {selectedSceneItem && (
            <div style={styles.panelCard}>
              <div style={styles.panelTitle}>RASTER VISUALIZATION (RGB)</div>
              {rgbError && <div style={styles.errorSmall}>{rgbError}</div>}

              {selectedSceneItem.has_rgb ? (
                <div>
                  <button
                    style={styles.renderBtn}
                    onClick={() => loadRGBVisualization(selectedSceneItem.scene_id, true)}
                    disabled={isRenderingRgb}
                  >
                    {isRenderingRgb ? 'REPROJECTING & RENDERING...' : rgbData ? 'RE-GENERATE RGB LAYER' : 'LOAD & DISPLAY RGB'}
                  </button>
                  <p style={styles.disclaimerText}>
                    * Aligns B04 (Red), B03 (Green), B02 (Blue), reprojects to EPSG:4326 and applies percentile contrast stretch.
                  </p>
                </div>
              ) : (
                <div style={styles.emptyNote}>
                  Scene missing required RGB bands (B04, B03, B02). Please download them in the Satellite tab.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Side: Leaflet Interactive Map */}
        <div style={styles.mapWrapper}>
          <MapContainer
            center={[19.7, 85.3]}
            zoom={10}
            style={styles.mapContainer}
            scrollWheelZoom={true}
          >
            {/* Auto camera bounds listener */}
            <FitBoundsHelper bounds={targetBounds} />

            {/* Base Tile Layer */}
            {showBaseMap && (
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxZoom={19}
              />
            )}

            {/* Vector Water Bodies GeoJSON Layer */}
            {showWaterBodies && geoJsonData && (
              <GeoJSON
                data={geoJsonData}
                style={(feature) => ({
                  color: feature?.properties.id === selectedWaterBodyId ? '#c2410c' : '#15803d',
                  weight: feature?.properties.id === selectedWaterBodyId ? 3 : 1.5,
                  fillColor: '#22c55e',
                  fillOpacity: feature?.properties.id === selectedWaterBodyId ? 0.35 : 0.15,
                })}
                onEachFeature={(feature, layer) => {
                  layer.on({
                    click: () => handleSelectWaterBody(feature.properties.id, feature.properties),
                  });
                  layer.bindPopup(
                    `<div style="font-family: sans-serif; font-size: 12px; line-height: 1.4;">
                      <strong style="color: #15803d; font-size: 13px;">${feature.properties.name}</strong><br/>
                      <b>Country:</b> ${feature.properties.country || 'N/A'}<br/>
                      <b>Type:</b> ${feature.properties.water_body_type || 'Inland Water'}<br/>
                      <b>Source:</b> ${feature.properties.source}<br/>
                      <b>Area:</b> ${feature.properties.area_sq_km ? Number(feature.properties.area_sq_km).toFixed(2) + ' km²' : 'N/A'}
                    </div>`
                  );
                }}
              />
            )}

            {/* Satellite Scene Footprint Layer */}
            {showSceneFootprint && selectedSceneItem?.footprint && (
              <GeoJSON
                key={`footprint-${selectedSceneItem.scene_id}`}
                data={selectedSceneItem.footprint}
                style={{
                  color: '#ea580c',
                  weight: 2,
                  dashArray: '5, 5',
                  fillColor: '#fff7ed',
                  fillOpacity: 0.08,
                }}
              />
            )}

            {/* Actual Sentinel-2 Reprojected RGB ImageOverlay Layer */}
            {showRgbImagery && rgbData && rasterOverlayBounds && (
              <ImageOverlay
                key={`rgb-overlay-${rgbData.scene_id}`}
                url={getSceneRGBImageUrl(rgbData.scene_id)}
                bounds={rasterOverlayBounds}
                opacity={rasterOpacity}
              />
            )}
          </MapContainer>

          {/* Floating Map Legend */}
          <div style={styles.mapLegend}>
            <div style={styles.legendTitle}>MAP SYMBOLOGY</div>
            <div style={styles.legendItem}>
              <span style={{ ...styles.legendBox, backgroundColor: 'rgba(34, 197, 94, 0.3)', borderColor: '#15803d' }}></span>
              <span>Water Body Boundary</span>
            </div>
            <div style={styles.legendItem}>
              <span style={{ ...styles.legendBox, backgroundColor: 'rgba(194, 65, 12, 0.4)', borderColor: '#c2410c' }}></span>
              <span>Selected Water Body</span>
            </div>
            <div style={styles.legendItem}>
              <span style={{ ...styles.legendLine, borderColor: '#ea580c', borderStyle: 'dashed' }}></span>
              <span>Scene Footprint</span>
            </div>
            <div style={styles.legendItem}>
              <span style={{ ...styles.legendBox, backgroundColor: '#38bdf8', borderColor: '#0284c7' }}></span>
              <span>Sentinel-2 L2A RGB Raster</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Panel: Selected Scene & Raster Details */}
      {sceneMetadata && (
        <div style={styles.bottomPanel}>
          <div style={styles.panelTitle}>RASTER METADATA & SENSING ATTRIBUTES</div>
          <div style={styles.metaGrid}>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>SCENE IDENTIFIER:</span>
              <span style={styles.metaCellVal}>{sceneMetadata.external_scene_id}</span>
            </div>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>NATIVE CRS:</span>
              <span style={styles.metaCellVal}>{sceneMetadata.crs || 'UTM (Auto-detected)'}</span>
            </div>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>DISPLAY CRS:</span>
              <span style={styles.metaCellVal}>EPSG:4326 (WGS84 Lat/Lon)</span>
            </div>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>CLOUD COVER:</span>
              <span style={styles.metaCellVal}>{sceneMetadata.cloud_cover_percent != null ? `${sceneMetadata.cloud_cover_percent.toFixed(2)}%` : 'N/A'}</span>
            </div>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>VISUALIZATION PRODUCT:</span>
              <span style={styles.metaCellVal}>True-Color RGB (B04/B03/B02) 2-98% Percentile Stretch</span>
            </div>
            <div style={styles.metaCell}>
              <span style={styles.metaCellKey}>GEOGRAPHIC BOUNDS (W, S, E, N):</span>
              <span style={styles.metaCellVal}>
                {sceneMetadata.geographic_bounds
                  ? `[${sceneMetadata.geographic_bounds.west.toFixed(4)}, ${sceneMetadata.geographic_bounds.south.toFixed(4)}, ${sceneMetadata.geographic_bounds.east.toFixed(4)}, ${sceneMetadata.geographic_bounds.north.toFixed(4)}]`
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  headerBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem 1.25rem',
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    borderLeft: '4px solid var(--color-primary)',
  },
  headerTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    color: 'var(--color-text-primary)',
    marginBottom: '0.25rem',
  },
  headerSubtitle: {
    fontSize: '0.8rem',
    color: 'var(--color-text-secondary)',
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.35rem 0.65rem',
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    fontSize: '0.75rem',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    color: 'var(--color-primary)',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary)',
  },
  errorBox: {
    padding: '0.75rem 1rem',
    backgroundColor: '#fef2f2',
    border: '1px solid #f87171',
    color: '#991b1b',
    fontSize: '0.85rem',
  },
  workspace: {
    display: 'grid',
    gridTemplateColumns: '360px 1fr',
    gap: '1rem',
    minHeight: '620px',
  },
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    maxHeight: '680px',
    overflowY: 'auto',
  },
  panelCard: {
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    padding: '1rem',
  },
  panelTitle: {
    fontSize: '0.75rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    color: 'var(--color-primary-dark)',
    marginBottom: '0.75rem',
    borderBottom: '1px solid var(--border-color)',
    paddingBottom: '0.35rem',
  },
  layerRow: {
    marginBottom: '0.5rem',
  },
  layerLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    cursor: 'pointer',
  },
  layerText: {
    fontSize: '0.8rem',
    fontWeight: 500,
    color: 'var(--color-text-primary)',
  },
  sliderContainer: {
    marginTop: '0.75rem',
    paddingTop: '0.75rem',
    borderTop: '1px dashed var(--border-color)',
  },
  sliderHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.75rem',
    fontWeight: 600,
    marginBottom: '0.25rem',
    color: 'var(--color-text-secondary)',
  },
  sliderValue: {
    fontFamily: 'var(--font-mono)',
    color: 'var(--color-primary)',
  },
  slider: {
    width: '100%',
    cursor: 'pointer',
  },
  select: {
    width: '100%',
    padding: '0.5rem',
    border: '1px solid var(--border-color)',
    backgroundColor: 'var(--color-surface)',
    fontSize: '0.8rem',
    fontFamily: 'inherit',
    marginBottom: '0.5rem',
  },
  metaBox: {
    padding: '0.5rem',
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    fontSize: '0.75rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  metaRow: {
    display: 'flex',
    justifyContent: 'space-between',
  },
  metaKey: {
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
  },
  fitBtn: {
    marginTop: '0.5rem',
    padding: '0.35rem',
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    color: 'var(--color-primary)',
    fontWeight: 700,
    fontSize: '0.7rem',
    cursor: 'pointer',
  },
  sceneList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    maxHeight: '180px',
    overflowY: 'auto',
  },
  sceneCard: {
    padding: '0.5rem',
    border: '1px solid var(--border-color)',
    cursor: 'pointer',
    fontSize: '0.75rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.2rem',
  },
  sceneHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sceneIdText: {
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
    fontSize: '0.7rem',
    color: 'var(--color-text-primary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '190px',
  },
  sceneMetaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.7rem',
    color: 'var(--color-text-secondary)',
  },
  badgeSuccess: {
    fontSize: '0.65rem',
    fontWeight: 700,
    backgroundColor: '#dcfce7',
    color: '#15803d',
    padding: '0.1rem 0.35rem',
  },
  badgeWarn: {
    fontSize: '0.65rem',
    fontWeight: 700,
    backgroundColor: '#fef3c7',
    color: '#b45309',
    padding: '0.1rem 0.35rem',
  },
  renderBtn: {
    width: '100%',
    padding: '0.5rem',
    backgroundColor: 'var(--color-primary)',
    color: '#ffffff',
    border: 'none',
    fontWeight: 700,
    fontSize: '0.75rem',
    letterSpacing: '0.04em',
    cursor: 'pointer',
    marginBottom: '0.4rem',
  },
  disclaimerText: {
    fontSize: '0.68rem',
    color: 'var(--color-text-muted)',
    lineHeight: 1.3,
  },
  emptyNote: {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
  errorSmall: {
    color: '#b91c1c',
    fontSize: '0.72rem',
    marginBottom: '0.4rem',
  },
  mapWrapper: {
    position: 'relative',
    border: '1px solid var(--border-color)',
    minHeight: '620px',
  },
  mapContainer: {
    width: '100%',
    height: '100%',
    minHeight: '620px',
  },
  mapLegend: {
    position: 'absolute',
    bottom: '20px',
    right: '20px',
    zIndex: 1000,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    border: '1px solid var(--border-color)',
    padding: '0.65rem 0.85rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
    fontSize: '0.72rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
  },
  legendTitle: {
    fontWeight: 700,
    letterSpacing: '0.04em',
    color: 'var(--color-text-secondary)',
    borderBottom: '1px solid var(--border-color)',
    paddingBottom: '0.2rem',
    marginBottom: '0.2rem',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  legendBox: {
    width: '14px',
    height: '14px',
    border: '1px solid',
  },
  legendLine: {
    width: '14px',
    borderTop: '2px dashed',
  },
  bottomPanel: {
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    padding: '1rem',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '0.75rem',
  },
  metaCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
    padding: '0.5rem',
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
  },
  metaCellKey: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: 'var(--color-text-muted)',
    letterSpacing: '0.03em',
  },
  metaCellVal: {
    fontSize: '0.75rem',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    color: 'var(--color-text-primary)',
    wordBreak: 'break-all',
  },
};
