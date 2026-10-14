import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  getWaterBodiesGeoJson,
  getWaterBodyTemporalAnalysis,
  resolveApiUrl,
  TemporalAnalysisResponse,
  ObservationTimelineItem,
  WaterBody,
} from '../api/client';
import { FetchVisualDataModal } from '../components/FetchVisualDataModal';

interface AnalysisPageProps {
  initialWaterBodyId?: string;
  onNavigateToMap?: (waterBodyId?: string) => void;
}

export const AnalysisPage: React.FC<AnalysisPageProps> = ({
  initialWaterBodyId,
  onNavigateToMap,
}) => {
  const [waterBodies, setWaterBodies] = useState<WaterBody[]>([]);
  const [selectedWaterBodyId, setSelectedWaterBodyId] = useState<string>(
    initialWaterBodyId || localStorage.getItem('jalnetra_selected_wb_id') || ''
  );
  const [analysisData, setAnalysisData] = useState<TemporalAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Comparison state
  const [compareId1, setCompareId1] = useState<string>('');
  const [compareId2, setCompareId2] = useState<string>('');
  const [comparisonMode, setComparisonMode] = useState<'side-by-side' | 'slider'>('side-by-side');
  const [sliderPos, setSliderPos] = useState<number>(50); // percentage 0-100

  // Expanded Image Modal
  const [expandedImage, setExpandedImage] = useState<ObservationTimelineItem | null>(null);

  // Fetch Visual Data Modal
  const [isFetchModalOpen, setIsFetchModalOpen] = useState<boolean>(false);

  // Load registered water bodies
  useEffect(() => {
    let active = true;
    getWaterBodiesGeoJson()
      .then(geoJson => {
        if (!active) return;
        const wbs: WaterBody[] = (geoJson.features || []).map((f: any) => ({
          id: f.properties.id,
          name: f.properties.name,
          normalized_name: f.properties.normalized_name || f.properties.name.toLowerCase(),
          country: f.properties.country,
          source: f.properties.source,
          water_body_type: f.properties.water_body_type,
          area_sq_km: f.properties.area_sq_km,
          centroid_lat: f.properties.centroid_lat,
          centroid_lon: f.properties.centroid_lon,
          min_lat: f.properties.min_lat,
          min_lon: f.properties.min_lon,
          max_lat: f.properties.max_lat,
          max_lon: f.properties.max_lon,
        }));
        setWaterBodies(wbs);
        if (!selectedWaterBodyId && wbs.length > 0) {
          setSelectedWaterBodyId(wbs[0].id);
        }
      })
      .catch(err => {
        console.error('Failed to load water bodies:', err);
      });
    return () => { active = false; };
  }, []);

  // Load temporal analysis data when water body changes
  const loadAnalysis = useCallback(async (wbId: string) => {
    if (!wbId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getWaterBodyTemporalAnalysis(wbId);
      setAnalysisData(data);
      if (data.timeline.length > 0) {
        setCompareId1(data.timeline[0].id);
        setCompareId2(data.timeline[data.timeline.length - 1].id);
      } else {
        setCompareId1('');
        setCompareId2('');
      }
    } catch (err: any) {
      console.error('Failed to load temporal analysis:', err);
      setError(err.message || 'Failed to load analysis for water body');
      setAnalysisData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedWaterBodyId) {
      localStorage.setItem('jalnetra_selected_wb_id', selectedWaterBodyId);
      loadAnalysis(selectedWaterBodyId);
    }
  }, [selectedWaterBodyId, loadAnalysis]);

  const selectedWaterBody = useMemo(() => {
    return waterBodies.find(wb => wb.id === selectedWaterBodyId);
  }, [waterBodies, selectedWaterBodyId]);

  const obs1 = useMemo(() => {
    return analysisData?.timeline.find(t => t.id === compareId1);
  }, [analysisData, compareId1]);

  const obs2 = useMemo(() => {
    return analysisData?.timeline.find(t => t.id === compareId2);
  }, [analysisData, compareId2]);

  // Overall net change
  const netChange = useMemo(() => {
    if (!analysisData?.timeline || analysisData.timeline.length < 2) return null;
    const first = analysisData.timeline[0].water_extent_sq_km;
    const last = analysisData.timeline[analysisData.timeline.length - 1].water_extent_sq_km;
    if (first == null || last == null) return null;
    return last - first;
  }, [analysisData]);

  return (
    <div style={styles.container}>
      {/* ── Top Header Bar ──────────────────────────────────────────────── */}
      <div style={styles.topBar}>
        <div style={styles.topBarLeft}>
          <div style={styles.kicker}>WATER BODY TIME-SERIES MONITORING</div>
          <h2 style={styles.pageTitle}>Temporal Analysis Workstation</h2>
        </div>

        <div style={styles.topBarRight}>
          <div style={styles.selectorGroup}>
            <label style={styles.selectorLabel}>TARGET WATER BODY:</label>
            <select
              style={styles.wbSelect}
              value={selectedWaterBodyId}
              onChange={e => setSelectedWaterBodyId(e.target.value)}
              disabled={isLoading || waterBodies.length === 0}
            >
              {waterBodies.map(wb => (
                <option key={wb.id} value={wb.id}>
                  {wb.name} {wb.country ? `(${wb.country})` : ''}
                </option>
              ))}
            </select>
          </div>

          {selectedWaterBody && (
            <button
              style={styles.fetchBtn}
              onClick={() => setIsFetchModalOpen(true)}
            >
              + FETCH VISUAL DATA
            </button>
          )}

          {onNavigateToMap && (
            <button
              style={styles.mapNavBtn}
              onClick={() => onNavigateToMap(selectedWaterBodyId)}
            >
              🗺 OPEN MAP
            </button>
          )}
        </div>
      </div>

      {/* ── Main Content Area ───────────────────────────────────────────── */}
      <div style={styles.contentScroll}>
        {error && (
          <div style={styles.errorBanner}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Target Meta / Stats Banner */}
        {selectedWaterBody && (
          <div style={styles.metaBanner}>
            <div style={styles.statCell}>
              <span style={styles.statLabel}>WATER BODY</span>
              <span style={styles.statValuePrimary}>{selectedWaterBody.name}</span>
              <span style={styles.statSub}>{selectedWaterBody.water_body_type || 'lake'} • {selectedWaterBody.country || 'India'}</span>
            </div>
            <div style={styles.statCell}>
              <span style={styles.statLabel}>REGISTERED AREA</span>
              <span style={styles.statValue}>
                {selectedWaterBody.area_sq_km ? `${selectedWaterBody.area_sq_km.toFixed(2)} km²` : 'N/A'}
              </span>
              <span style={styles.statSub}>Target extent</span>
            </div>
            <div style={styles.statCell}>
              <span style={styles.statLabel}>OBSERVATIONS</span>
              <span style={styles.statValue}>
                {analysisData ? analysisData.total_observations : 0}
              </span>
              <span style={styles.statSub}>Acquired satellite dates</span>
            </div>
            <div style={styles.statCell}>
              <span style={styles.statLabel}>MONITORING PERIOD</span>
              <span style={styles.statValue}>
                {analysisData?.from_date && analysisData?.to_date
                  ? `${analysisData.from_date} → ${analysisData.to_date}`
                  : 'No observations'}
              </span>
              <span style={styles.statSub}>
                {netChange !== null
                  ? `Net extent change: ${netChange >= 0 ? '+' : ''}${netChange.toFixed(2)} km²`
                  : 'Temporal coverage'}
              </span>
            </div>
          </div>
        )}

        {/* If no observations yet */}
        {!isLoading && analysisData && analysisData.total_observations === 0 && (
          <div style={styles.emptyCard}>
            <div style={styles.emptyIcon}>🛰</div>
            <h3 style={styles.emptyTitle}>No Satellite Observations Acquired Yet</h3>
            <p style={styles.emptyDesc}>
              No visual satellite observations have been downloaded for &ldquo;{selectedWaterBody?.name}&rdquo;.
              Click <strong>&ldquo;Fetch Visual Data&rdquo;</strong> to discover and retrieve cloud-tolerant Sentinel-2 imagery distributed across any date range.
            </p>
            {selectedWaterBody && (
              <button
                style={styles.emptyActionBtn}
                onClick={() => setIsFetchModalOpen(true)}
              >
                + FETCH VISUAL DATA FOR {selectedWaterBody.name.toUpperCase()}
              </button>
            )}
          </div>
        )}

        {/* ── Section 1: Chronological Image Gallery ─────────────────────── */}
        {analysisData && analysisData.timeline.length > 0 && (
          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <div>
                <h3 style={styles.sectionTitle}>1. Chronological Observation History</h3>
                <span style={styles.sectionSubtitle}>
                  {analysisData.total_observations} Sentinel-2 RGB visual observations clipped to the target water-body AOI
                </span>
              </div>
            </div>

            <div style={styles.galleryGrid}>
              {analysisData.timeline.map((item, idx) => (
                <div
                  key={item.id}
                  style={styles.galleryCard}
                  onClick={() => setExpandedImage(item)}
                >
                  <div style={styles.thumbWrapper}>
                    <img
                      src={resolveApiUrl(item.image_url)}
                      alt={`${item.sensing_date_str}`}
                      style={styles.thumbImg}
                      loading="lazy"
                    />
                    <div style={styles.thumbDateBadge}>
                      {item.sensing_date_str}
                    </div>
                  </div>

                  <div style={styles.cardDetails}>
                    <div style={styles.cardDetailRow}>
                      <span>Quality:</span>
                      <span
                        style={{
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          padding: '0.1rem 0.35rem',
                          borderRadius: '2px',
                          backgroundColor:
                            item.quality_label === 'VERY CLEAR' ? '#ecfdf5' :
                            item.quality_label === 'CLEAR' ? '#eff6ff' :
                            item.quality_label === 'ACCEPTABLE' ? '#fffbeb' : '#fef2f2',
                          color:
                            item.quality_label === 'VERY CLEAR' ? '#065f46' :
                            item.quality_label === 'CLEAR' ? '#1e40af' :
                            item.quality_label === 'ACCEPTABLE' ? '#92400e' : '#991b1b',
                        }}
                      >
                        {item.quality_label || (item.cloud_cover_percent != null && item.cloud_cover_percent <= 10 ? 'VERY CLEAR' : item.cloud_cover_percent != null && item.cloud_cover_percent <= 25 ? 'CLEAR' : item.cloud_cover_percent != null && item.cloud_cover_percent <= 40 ? 'ACCEPTABLE' : 'HIGH CLOUD')}
                      </span>
                    </div>
                    <div style={styles.cardDetailRow}>
                      <span>Cloud Cover:</span>
                      <strong style={{ color: item.cloud_cover_percent != null && item.cloud_cover_percent > 30 ? '#d97706' : '#059669' }}>
                        {item.cloud_cover_percent != null ? `${item.cloud_cover_percent.toFixed(1)}%` : 'N/A'}
                      </strong>
                    </div>
                    <div style={styles.cardDetailRow}>
                      <span>Surface Extent:</span>
                      {item.is_extent_measured && item.water_extent_sq_km != null ? (
                        <strong>{item.water_extent_sq_km.toFixed(2)} km²</strong>
                      ) : (
                        <span style={{ color: '#64748b', fontSize: '0.68rem', fontStyle: 'italic' }}>
                          Unsegmented (Visual)
                        </span>
                      )}
                    </div>
                    {item.is_extent_measured && item.change_from_previous_sq_km != null && idx > 0 && (
                      <div style={styles.cardDetailRow}>
                        <span>Change:</span>
                        <strong style={{ color: item.change_from_previous_sq_km >= 0 ? '#16a34a' : '#dc2626' }}>
                          {item.change_from_previous_sq_km >= 0 ? '↑ +' : '↓ '}{item.change_from_previous_sq_km.toFixed(2)} km²
                        </strong>
                      </div>
                    )}
                    <div style={styles.cardFooter}>
                      <span>10m Sentinel-2</span>
                      <span style={{ color: '#0284c7', cursor: 'pointer' }}>Zoom 🔍</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 2: Temporal Comparison Tool ────────────────────────── */}
        {analysisData && analysisData.timeline.length >= 2 && (
          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <div>
                <h3 style={styles.sectionTitle}>2. Temporal Comparison</h3>
                <span style={styles.sectionSubtitle}>
                  Compare two observation dates to observe water spread, shoreline changes, and visual variations
                </span>
              </div>
              <div style={styles.compareModeToggle}>
                <button
                  style={{
                    ...styles.modeToggleBtn,
                    ...(comparisonMode === 'side-by-side' ? styles.modeToggleBtnActive : {}),
                  }}
                  onClick={() => setComparisonMode('side-by-side')}
                >
                  Side-by-Side
                </button>
                <button
                  style={{
                    ...styles.modeToggleBtn,
                    ...(comparisonMode === 'slider' ? styles.modeToggleBtnActive : {}),
                  }}
                  onClick={() => setComparisonMode('slider')}
                >
                  Slider Overlay
                </button>
              </div>
            </div>

            {/* Date Selection Dropdowns */}
            <div style={styles.comparePickersRow}>
              <div style={styles.comparePickerBox}>
                <label style={styles.pickerLabel}>OBSERVATION A (BEFORE):</label>
                <select
                  style={styles.pickerSelect}
                  value={compareId1}
                  onChange={e => setCompareId1(e.target.value)}
                >
                  {analysisData.timeline.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.sensing_date_str} {t.water_extent_sq_km ? `(${t.water_extent_sq_km.toFixed(2)} km²)` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div style={styles.vsBadge}>VS</div>

              <div style={styles.comparePickerBox}>
                <label style={styles.pickerLabel}>OBSERVATION B (AFTER):</label>
                <select
                  style={styles.pickerSelect}
                  value={compareId2}
                  onChange={e => setCompareId2(e.target.value)}
                >
                  {analysisData.timeline.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.sensing_date_str} {t.water_extent_sq_km ? `(${t.water_extent_sq_km.toFixed(2)} km²)` : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Comparison Views */}
            {obs1 && obs2 && (
              <>
                {comparisonMode === 'side-by-side' ? (
                  <div style={styles.sideBySideGrid}>
                    <div style={styles.compareViewport}>
                      <div style={styles.viewportHeader}>
                        <span>Date A: {obs1.sensing_date_str}</span>
                        {obs1.is_extent_measured && obs1.water_extent_sq_km != null ? (
                          <span>Extent: {obs1.water_extent_sq_km.toFixed(2)} km²</span>
                        ) : (
                          <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Visual observation</span>
                        )}
                      </div>
                      <img
                        src={resolveApiUrl(obs1.image_url)}
                        alt={obs1.sensing_date_str}
                        style={styles.compareImg}
                      />
                    </div>

                    <div style={styles.compareViewport}>
                      <div style={styles.viewportHeader}>
                        <span>Date B: {obs2.sensing_date_str}</span>
                        {obs2.is_extent_measured && obs2.water_extent_sq_km != null ? (
                          <span>Extent: {obs2.water_extent_sq_km.toFixed(2)} km²</span>
                        ) : (
                          <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Visual observation</span>
                        )}
                      </div>
                      <img
                        src={resolveApiUrl(obs2.image_url)}
                        alt={obs2.sensing_date_str}
                        style={styles.compareImg}
                      />
                    </div>
                  </div>
                ) : (
                  <div style={styles.sliderContainer}>
                    <div style={styles.sliderViewport}>
                      {/* Base Image (Date B) */}
                      <img
                        src={resolveApiUrl(obs2.image_url)}
                        alt={obs2.sensing_date_str}
                        style={styles.sliderImgBase}
                      />
                      {/* Clipped Top Image (Date A) */}
                      <div
                        style={{
                          ...styles.sliderClippedWrapper,
                          width: `${sliderPos}%`,
                        }}
                      >
                        <img
                          src={resolveApiUrl(obs1.image_url)}
                          alt={obs1.sensing_date_str}
                          style={styles.sliderImgTop}
                        />
                      </div>
                      {/* Divider line */}
                      <div
                        style={{
                          ...styles.sliderDivider,
                          left: `${sliderPos}%`,
                        }}
                      />
                    </div>

                    <div style={styles.sliderControlRow}>
                      <span style={styles.sliderLabelLeft}>◀ {obs1.sensing_date_str}</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={sliderPos}
                        onChange={e => setSliderPos(Number(e.target.value))}
                        style={styles.rangeInput}
                      />
                      <span style={styles.sliderLabelRight}>{obs2.sensing_date_str} ▶</span>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Section 3: Water Extent Time-Series Chart ──────────────────── */}
        {analysisData && analysisData.timeline.length > 0 && (
          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <div>
                <h3 style={styles.sectionTitle}>3. Apparent Water Extent Over Time</h3>
                <span style={styles.sectionSubtitle}>
                  Surface water area estimated from high-resolution Sentinel-2 observations
                </span>
              </div>
            </div>

            <div style={styles.chartWrapper}>
              <SimpleExtentChart timeline={analysisData.timeline} />
            </div>
          </div>
        )}

        {/* ── Section 4: Water Quality Indicators (Extensible Proxies) ────── */}
        <div style={styles.sectionCard}>
          <div style={styles.sectionHeader}>
            <div>
              <h3 style={styles.sectionTitle}>4. Remote-Sensing Water Quality Indicators</h3>
              <span style={styles.sectionSubtitle}>
                Spectral proxy indicators (turbidity, chlorophyll-a, algae, anomaly) designed for lazy on-demand spectral processing
              </span>
            </div>
          </div>

          <div style={styles.indicatorsGrid}>
            {analysisData?.indicators &&
              Object.values(analysisData.indicators).map(ind => (
                <div key={ind.id} style={styles.indicatorCard}>
                  <div style={styles.indHeader}>
                    <span style={styles.indLabel}>{ind.label}</span>
                    <span style={styles.indStatusBadge}>{ind.message}</span>
                  </div>
                  <p style={styles.indDesc}>{ind.description}</p>
                  <div style={styles.indFooter}>
                    <span>Index: {ind.unit || 'Normalized Proxy'}</span>
                    <span style={styles.indDisabledText}>Requires on-demand spectral bands</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* ── Image Expansion Modal ────────────────────────────────────────── */}
      {expandedImage && (
        <div style={styles.expandedOverlay} onClick={() => setExpandedImage(null)}>
          <div style={styles.expandedBox} onClick={e => e.stopPropagation()}>
            <div style={styles.expandedHeader}>
              <div>
                <div style={styles.kicker}>HIGH-RESOLUTION VISUAL OBSERVATION</div>
                <h3 style={{ margin: 0, fontSize: '1rem', color: '#0f172a' }}>
                  {selectedWaterBody?.name} • {expandedImage.sensing_date_str}
                </h3>
              </div>
              <button
                style={styles.closeBtn}
                onClick={() => setExpandedImage(null)}
              >
                ✕
              </button>
            </div>
            <img
              src={resolveApiUrl(expandedImage.image_url)}
              alt={expandedImage.sensing_date_str}
              style={styles.expandedImg}
            />
            <div style={styles.expandedFooter}>
              <span>Quality: <strong>{expandedImage.quality_label || 'VISUAL'}</strong></span>
              <span>Cloud cover: {expandedImage.cloud_cover_percent != null ? `${expandedImage.cloud_cover_percent.toFixed(1)}%` : 'N/A'}</span>
              <span>
                Surface extent: {expandedImage.is_extent_measured && expandedImage.water_extent_sq_km != null
                  ? `${expandedImage.water_extent_sq_km.toFixed(2)} km²`
                  : 'Unsegmented (Visual)'}
              </span>
              <span>Sensor: Sentinel-2 L2A (B04/B03/B02)</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Fetch Visual Data Modal ──────────────────────────────────────── */}
      {selectedWaterBody && (
        <FetchVisualDataModal
          waterBody={selectedWaterBody}
          isOpen={isFetchModalOpen}
          onClose={() => setIsFetchModalOpen(false)}
          onNavigateToAnalysis={wbId => loadAnalysis(wbId)}
        />
      )}
    </div>
  );
};

// ─── Simple SVG Line Chart Component ─────────────────────────────────────────
interface ChartProps {
  timeline: ObservationTimelineItem[];
}

const SimpleExtentChart: React.FC<ChartProps> = ({ timeline }) => {
  const pointsWithValues = timeline.filter(t => t.water_extent_sq_km != null);
  if (pointsWithValues.length === 0) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>No numeric extent values available to plot.</div>;
  }

  const values = pointsWithValues.map(p => p.water_extent_sq_km as number);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = Math.max(maxVal - minVal, 1.0);

  const paddingY = range * 0.15;
  const yMin = Math.max(0, minVal - paddingY);
  const yMax = maxVal + paddingY;
  const ySpan = yMax - yMin;

  const width = 800;
  const height = 220;
  const padLeft = 60;
  const padRight = 30;
  const padTop = 20;
  const padBottom = 40;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const coords = pointsWithValues.map((p, idx) => {
    const x = padLeft + (pointsWithValues.length > 1 ? (idx / (pointsWithValues.length - 1)) * chartW : chartW / 2);
    const y = padTop + chartH - (( (p.water_extent_sq_km as number) - yMin) / ySpan) * chartH;
    return { x, y, item: p };
  });

  const pathD = coords.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, '');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {/* Grid Lines */}
      <line x1={padLeft} y1={padTop} x2={width - padRight} y2={padTop} stroke="#e2e8f0" strokeDasharray="3 3" />
      <line x1={padLeft} y1={padTop + chartH / 2} x2={width - padRight} y2={padTop + chartH / 2} stroke="#e2e8f0" strokeDasharray="3 3" />
      <line x1={padLeft} y1={padTop + chartH} x2={width - padRight} y2={padTop + chartH} stroke="#cbd5e1" />

      {/* Y Axis Labels */}
      <text x={padLeft - 8} y={padTop + 4} textAnchor="end" fontSize="10" fill="#64748b" fontFamily="sans-serif">
        {yMax.toFixed(1)} km²
      </text>
      <text x={padLeft - 8} y={padTop + chartH / 2 + 3} textAnchor="end" fontSize="10" fill="#64748b" fontFamily="sans-serif">
        {((yMax + yMin) / 2).toFixed(1)} km²
      </text>
      <text x={padLeft - 8} y={padTop + chartH + 3} textAnchor="end" fontSize="10" fill="#64748b" fontFamily="sans-serif">
        {yMin.toFixed(1)} km²
      </text>

      {/* Line Path */}
      {coords.length > 1 && (
        <path d={pathD} fill="none" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      )}

      {/* Points */}
      {coords.map((pt) => (
        <g key={pt.item.id}>
          <circle cx={pt.x} cy={pt.y} r="5" fill="#0284c7" stroke="#ffffff" strokeWidth="2" />
          <text
            x={pt.x}
            y={height - 12}
            textAnchor="middle"
            fontSize="9"
            fill="#475569"
            fontFamily="sans-serif"
          >
            {pt.item.sensing_date_str.slice(5)}
          </text>
          <text
            x={pt.x}
            y={pt.y - 9}
            textAnchor="middle"
            fontSize="9"
            fontWeight="bold"
            fill="#0f172a"
            fontFamily="sans-serif"
          >
            {pt.item.water_extent_sq_km?.toFixed(1)}
          </text>
        </g>
      ))}
    </svg>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    backgroundColor: '#f8fafc',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  topBar: {
    padding: '0.85rem 1.5rem',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  topBarLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.1rem',
  },
  kicker: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#0284c7',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  pageTitle: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#0f172a',
    letterSpacing: '-0.01em',
  },
  topBarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  selectorGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  selectorLabel: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#475569',
  },
  wbSelect: {
    padding: '0.4rem 0.65rem',
    border: '1px solid #cbd5e1',
    borderRadius: '3px',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#0f172a',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  fetchBtn: {
    padding: '0.45rem 0.85rem',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '3px',
    fontSize: '0.72rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.02em',
  },
  mapNavBtn: {
    padding: '0.45rem 0.85rem',
    backgroundColor: '#f1f5f9',
    color: '#334155',
    border: '1px solid #cbd5e1',
    borderRadius: '3px',
    fontSize: '0.72rem',
    fontWeight: 700,
    cursor: 'pointer',
  },
  contentScroll: {
    flex: 1,
    overflowY: 'auto',
    padding: '1.25rem 1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  errorBanner: {
    padding: '0.75rem 1rem',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '3px',
    color: '#991b1b',
    fontSize: '0.8rem',
  },
  metaBanner: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '0.75rem',
    backgroundColor: '#ffffff',
    padding: '1rem',
    borderRadius: '4px',
    border: '1px solid #e2e8f0',
  },
  statCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
  },
  statLabel: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.04em',
  },
  statValuePrimary: {
    fontSize: '1.1rem',
    fontWeight: 800,
    color: '#0f172a',
  },
  statValue: {
    fontSize: '1.05rem',
    fontWeight: 700,
    color: '#0284c7',
  },
  statSub: {
    fontSize: '0.68rem',
    color: '#64748b',
  },
  emptyCard: {
    padding: '3rem 2rem',
    backgroundColor: '#ffffff',
    border: '1px dashed #cbd5e1',
    borderRadius: '4px',
    textAlign: 'center',
    maxWidth: '560px',
    margin: '2rem auto',
  },
  emptyIcon: {
    fontSize: '2.5rem',
    marginBottom: '0.5rem',
  },
  emptyTitle: {
    margin: '0 0 0.5rem',
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#0f172a',
  },
  emptyDesc: {
    fontSize: '0.8rem',
    color: '#64748b',
    lineHeight: 1.5,
    margin: '0 0 1.25rem',
  },
  emptyActionBtn: {
    padding: '0.6rem 1.25rem',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '3px',
    fontSize: '0.75rem',
    fontWeight: 700,
    cursor: 'pointer',
  },
  sectionCard: {
    backgroundColor: '#ffffff',
    borderRadius: '4px',
    border: '1px solid #e2e8f0',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: '0.5rem',
    borderBottom: '1px solid #f1f5f9',
    paddingBottom: '0.75rem',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '0.95rem',
    fontWeight: 800,
    color: '#0f172a',
    letterSpacing: '-0.01em',
  },
  sectionSubtitle: {
    fontSize: '0.72rem',
    color: '#64748b',
  },
  galleryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '1rem',
  },
  galleryCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
    transition: 'transform 0.15s, box-shadow 0.15s',
  },
  thumbWrapper: {
    position: 'relative',
    width: '100%',
    paddingTop: '75%',
    backgroundColor: '#0f172a',
  },
  thumbImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  thumbDateBadge: {
    position: 'absolute',
    bottom: '6px',
    left: '6px',
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    color: '#ffffff',
    fontSize: '0.65rem',
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: '2px',
    fontFamily: 'monospace',
  },
  cardDetails: {
    padding: '0.65rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.3rem',
    fontSize: '0.7rem',
  },
  cardDetailRow: {
    display: 'flex',
    justifyContent: 'space-between',
    color: '#475569',
  },
  cardFooter: {
    borderTop: '1px solid #f1f5f9',
    paddingTop: '0.4rem',
    marginTop: '0.2rem',
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.65rem',
    color: '#94a3b8',
  },
  compareModeToggle: {
    display: 'flex',
    border: '1px solid #cbd5e1',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  modeToggleBtn: {
    padding: '0.35rem 0.75rem',
    backgroundColor: '#f8fafc',
    border: 'none',
    fontSize: '0.72rem',
    fontWeight: 600,
    color: '#475569',
    cursor: 'pointer',
  },
  modeToggleBtnActive: {
    backgroundColor: '#0284c7',
    color: '#ffffff',
    fontWeight: 700,
  },
  comparePickersRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    flexWrap: 'wrap',
    padding: '0.5rem 0.75rem',
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '3px',
  },
  comparePickerBox: {
    flex: 1,
    minWidth: '200px',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.2rem',
  },
  pickerLabel: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#475569',
  },
  pickerSelect: {
    padding: '0.4rem 0.6rem',
    border: '1px solid #cbd5e1',
    borderRadius: '3px',
    fontSize: '0.75rem',
    color: '#0f172a',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  vsBadge: {
    fontSize: '0.75rem',
    fontWeight: 800,
    color: '#0284c7',
    padding: '0.2rem 0.5rem',
  },
  sideBySideGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1rem',
  },
  compareViewport: {
    border: '1px solid #cbd5e1',
    borderRadius: '3px',
    overflow: 'hidden',
    backgroundColor: '#0f172a',
  },
  viewportHeader: {
    padding: '0.4rem 0.75rem',
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    color: '#ffffff',
    fontSize: '0.7rem',
    fontWeight: 600,
    display: 'flex',
    justifyContent: 'space-between',
  },
  compareImg: {
    width: '100%',
    height: 'auto',
    maxHeight: '380px',
    objectFit: 'contain',
    display: 'block',
  },
  sliderContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
    alignItems: 'center',
  },
  sliderViewport: {
    position: 'relative',
    width: '100%',
    maxWidth: '680px',
    height: '400px',
    overflow: 'hidden',
    backgroundColor: '#0f172a',
    borderRadius: '3px',
    border: '1px solid #cbd5e1',
  },
  sliderImgBase: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  sliderClippedWrapper: {
    position: 'absolute',
    top: 0,
    left: 0,
    height: '100%',
    overflow: 'hidden',
  },
  sliderImgTop: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '680px',
    height: '100%',
    objectFit: 'contain',
  },
  sliderDivider: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: '3px',
    backgroundColor: '#ffffff',
    boxShadow: '0 0 5px rgba(0,0,0,0.5)',
    transform: 'translateX(-50%)',
    pointerEvents: 'none',
  },
  sliderControlRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    width: '100%',
    maxWidth: '680px',
  },
  sliderLabelLeft: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#0284c7',
  },
  sliderLabelRight: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#0284c7',
  },
  rangeInput: {
    flex: 1,
    cursor: 'pointer',
  },
  chartWrapper: {
    padding: '0.5rem',
    backgroundColor: '#ffffff',
    border: '1px solid #f1f5f9',
    borderRadius: '3px',
  },
  indicatorsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '0.75rem',
  },
  indicatorCard: {
    padding: '0.85rem',
    border: '1px dashed #cbd5e1',
    borderRadius: '4px',
    backgroundColor: '#f8fafc',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  },
  indHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '0.4rem',
  },
  indLabel: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#1e293b',
  },
  indStatusBadge: {
    fontSize: '0.58rem',
    fontWeight: 700,
    color: '#475569',
    backgroundColor: '#e2e8f0',
    padding: '0.12rem 0.4rem',
    borderRadius: '2px',
  },
  indDesc: {
    fontSize: '0.68rem',
    color: '#64748b',
    lineHeight: 1.35,
    margin: 0,
  },
  indFooter: {
    borderTop: '1px solid #e2e8f0',
    paddingTop: '0.35rem',
    marginTop: 'auto',
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.62rem',
    color: '#94a3b8',
  },
  indDisabledText: {
    fontStyle: 'italic',
  },
  expandedOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 99999,
    padding: '1.5rem',
  },
  expandedBox: {
    backgroundColor: '#ffffff',
    borderRadius: '4px',
    overflow: 'hidden',
    maxWidth: '800px',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  expandedHeader: {
    padding: '0.85rem 1.25rem',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  expandedImg: {
    width: '100%',
    maxHeight: '70vh',
    objectFit: 'contain',
    backgroundColor: '#0f172a',
  },
  expandedFooter: {
    padding: '0.65rem 1.25rem',
    backgroundColor: '#f8fafc',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.72rem',
    color: '#475569',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '1.1rem',
    color: '#64748b',
    cursor: 'pointer',
  },
};
