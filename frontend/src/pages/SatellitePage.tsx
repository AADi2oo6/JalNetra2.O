import React, { useState, useEffect } from 'react';
import {
  listWaterBodies,
  searchSatelliteScenes,
  acquireSceneAssets,
  WaterBody,
  NormalizedScene,
  SceneAcquisitionResponse,
} from '../api';

const DEFAULT_TARGET_BANDS = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL'];

export const SatellitePage: React.FC = () => {
  const [waterBodies, setWaterBodies] = useState<WaterBody[]>([]);
  const [selectedWbId, setSelectedWbId] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-04-01');
  const [maxCloud, setMaxCloud] = useState<number>(20);
  const [limit, setLimit] = useState<number>(5);

  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [scenes, setScenes] = useState<NormalizedScene[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Scene Selection & Acquisition State
  const [selectedScene, setSelectedScene] = useState<NormalizedScene | null>(null);
  const [selectedBands, setSelectedBands] = useState<string[]>(DEFAULT_TARGET_BANDS);
  const [isAcquiring, setIsAcquiring] = useState<boolean>(false);
  const [acquisitionResult, setAcquisitionResult] = useState<SceneAcquisitionResponse | null>(null);
  const [acqError, setAcqError] = useState<string | null>(null);

  useEffect(() => {
    listWaterBodies(100, 0)
      .then((res) => {
        setWaterBodies(res.items);
        if (res.items.length > 0) {
          setSelectedWbId(res.items[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWbId) return;

    setIsSearching(true);
    setSearchError(null);
    setScenes([]);
    setSelectedScene(null);
    setAcquisitionResult(null);
    setAcqError(null);

    try {
      const sDate = startDate ? `${startDate}T00:00:00Z` : undefined;
      const eDate = endDate ? `${endDate}T23:59:59Z` : undefined;

      const resp = await searchSatelliteScenes(
        selectedWbId,
        sDate,
        eDate,
        maxCloud,
        limit
      );
      setScenes(resp.results);
      if (resp.results.length === 0) {
        setSearchError('No Sentinel-2 L2A scenes found matching spatial & cloud cover filters.');
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSearchError(err.message);
      } else {
        setSearchError('Error querying satellite STAC provider.');
      }
    } finally {
      setIsSearching(false);
    }
  };

  const toggleBand = (band: string) => {
    setSelectedBands((prev) =>
      prev.includes(band) ? prev.filter((b) => b !== band) : [...prev, band]
    );
  };

  const handleAcquire = async () => {
    if (!selectedScene || selectedBands.length === 0) return;

    setIsAcquiring(true);
    setAcqError(null);
    setAcquisitionResult(null);

    try {
      const resp = await acquireSceneAssets(selectedScene.external_scene_id, selectedBands);
      setAcquisitionResult(resp);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setAcqError(err.message);
      } else {
        setAcqError('Failed to acquire assets.');
      }
    } finally {
      setIsAcquiring(false);
    }
  };

  const activeWaterBody = waterBodies.find((w) => w.id === selectedWbId);

  return (
    <div style={styles.container}>
      {/* Search Configuration Section */}
      <section style={styles.card}>
        <div style={styles.header}>
          <h2 style={styles.title}>SENTINEL-2 SATELLITE DISCOVERY & ACQUISITION</h2>
          <div style={styles.providerBadge}>
            PROVIDER: EARTH SEARCH / AWS (PUBLIC COG)
          </div>
        </div>

        <p style={styles.desc}>
          Search public Sentinel-2 L2A surface reflectance scenes spatially intersecting the selected
          water body. Filter by datetime window and cloud cover percentage, rank by overlap & recency,
          and stream-download target spectral bands to local disk.
        </p>

        <form onSubmit={handleSearch} style={styles.formGrid}>
          <div>
            <label style={styles.label}>TARGET WATER BODY</label>
            <select
              value={selectedWbId}
              onChange={(e) => setSelectedWbId(e.target.value)}
              style={styles.select}
              disabled={isSearching || waterBodies.length === 0}
            >
              {waterBodies.map((wb) => (
                <option key={wb.id} value={wb.id}>
                  {wb.name} ({wb.country || 'Global'} - {wb.source})
                </option>
              ))}
              {waterBodies.length === 0 && (
                <option value="">No water bodies in catalog (Import one first)</option>
              )}
            </select>
          </div>

          <div>
            <label style={styles.label}>START DATE</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={styles.input}
              disabled={isSearching}
            />
          </div>

          <div>
            <label style={styles.label}>END DATE</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={styles.input}
              disabled={isSearching}
            />
          </div>

          <div>
            <label style={styles.label}>MAX CLOUD COVER (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={maxCloud}
              onChange={(e) => setMaxCloud(Number(e.target.value))}
              style={styles.input}
              disabled={isSearching}
            />
          </div>

          <div>
            <label style={styles.label}>LIMIT</label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={styles.select}
              disabled={isSearching}
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              type="submit"
              style={styles.btnPrimary}
              disabled={isSearching || !selectedWbId}
            >
              {isSearching ? 'SEARCHING STAC...' : 'SEARCH SCENES'}
            </button>
          </div>
        </form>

        {activeWaterBody && (
          <div style={styles.wbInfoBanner}>
            <span>
              <strong>Target Coordinates:</strong>{' '}
              {activeWaterBody.centroid_lat != null && activeWaterBody.centroid_lon != null
                ? `Centroid (${activeWaterBody.centroid_lat.toFixed(4)}, ${activeWaterBody.centroid_lon.toFixed(4)})`
                : 'Bounding box only'}
            </span>
            <span>
              <strong>Geometry:</strong>{' '}
              {activeWaterBody.geometry_geojson ? 'Polygon Geometry Active' : 'Point/Box Bounding'}
            </span>
          </div>
        )}

        {searchError && <div style={styles.errorBanner}>{searchError}</div>}
      </section>

      {/* STAC Results Table */}
      {scenes.length > 0 && (
        <section style={styles.card}>
          <div style={styles.header}>
            <h3 style={styles.title}>
              DISCOVERED SENTINEL-2 SCENES ({scenes.length} CANDIDATES - RANKED)
            </h3>
          </div>

          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>RANK SCORE</th>
                  <th style={styles.th}>SENSING DATE</th>
                  <th style={styles.th}>CLOUD COVER</th>
                  <th style={styles.th}>PROCESSING</th>
                  <th style={styles.th}>SCENE IDENTIFIER</th>
                  <th style={styles.th}>AVAILABLE ASSETS</th>
                  <th style={styles.th}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {scenes.map((scene) => {
                  const isSelected = selectedScene?.external_scene_id === scene.external_scene_id;
                  const assetKeys = Object.keys(scene.assets);

                  return (
                    <tr
                      key={scene.external_scene_id}
                      style={{
                        backgroundColor: isSelected ? 'var(--color-primary-subtle)' : 'transparent',
                      }}
                    >
                      <td style={styles.tdBold}>
                        <span style={styles.scorePill}>{scene.score ?? '-'}</span>
                      </td>
                      <td style={styles.tdMono}>
                        {new Date(scene.sensing_start).toLocaleDateString()} {new Date(scene.sensing_start).toLocaleTimeString()}
                      </td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.cloudPill,
                            color: (scene.cloud_cover_percent || 0) < 15 ? 'var(--color-primary-dark)' : 'var(--color-accent)',
                          }}
                        >
                          {scene.cloud_cover_percent != null ? `${scene.cloud_cover_percent.toFixed(1)}%` : '-'}
                        </span>
                      </td>
                      <td style={styles.tdMono}>{scene.processing_level || 'L2A'}</td>
                      <td style={styles.tdMono}>{scene.external_scene_id}</td>
                      <td style={styles.td}>
                        <span style={styles.assetCountPill}>
                          {assetKeys.filter((k) => DEFAULT_TARGET_BANDS.includes(k)).length} Core Bands / {assetKeys.length} Total
                        </span>
                      </td>
                      <td style={styles.td}>
                        <button
                          type="button"
                          style={{
                            ...styles.btnSelect,
                            backgroundColor: isSelected ? 'var(--color-primary)' : 'var(--color-surface-subtle)',
                            color: isSelected ? '#ffffff' : 'var(--color-text-primary)',
                          }}
                          onClick={() => {
                            setSelectedScene(scene);
                            setAcquisitionResult(null);
                            setAcqError(null);
                          }}
                        >
                          {isSelected ? 'SELECTED' : 'INSPECT & ACQUIRE'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Asset Selection & Acquisition Action Panel */}
      {selectedScene && (
        <section style={styles.acqPanel}>
          <div style={styles.header}>
            <h3 style={styles.title}>
              ACQUISITION INSPECTOR: {selectedScene.external_scene_id}
            </h3>
            <button style={styles.closeBtn} onClick={() => setSelectedScene(null)}>
              CLOSE
            </button>
          </div>

          <div style={styles.sceneMetaRow}>
            <div>
              <strong>Collection:</strong> {selectedScene.collection}
            </div>
            <div>
              <strong>Cloud Cover:</strong> {selectedScene.cloud_cover_percent?.toFixed(1)}%
            </div>
            <div>
              <strong>Date:</strong> {new Date(selectedScene.sensing_start).toISOString()}
            </div>
          </div>

          <div style={{ marginTop: '0.75rem' }}>
            <label style={styles.label}>SELECT SPECTRAL ASSETS TO ACQUIRE LOCALLY:</label>
            <div style={styles.bandCheckboxGroup}>
              {['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL', 'thumbnail'].map((bKey) => {
                const isAvailable = Boolean(selectedScene.assets[bKey]);
                const isChecked = selectedBands.includes(bKey);

                return (
                  <label
                    key={bKey}
                    style={{
                      ...styles.bandLabel,
                      opacity: isAvailable ? 1 : 0.4,
                      borderColor: isChecked ? 'var(--color-primary)' : 'var(--border-color)',
                      backgroundColor: isChecked ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={!isAvailable || isAcquiring}
                      onChange={() => toggleBand(bKey)}
                    />
                    <span>{bKey}</span>
                    <span style={styles.bandHint}>
                      {bKey === 'B02' && '(Blue 10m)'}
                      {bKey === 'B03' && '(Green 10m)'}
                      {bKey === 'B04' && '(Red 10m)'}
                      {bKey === 'B08' && '(NIR 10m)'}
                      {bKey === 'B11' && '(SWIR1 20m)'}
                      {bKey === 'B12' && '(SWIR2 20m)'}
                      {bKey === 'SCL' && '(Scene Class)'}
                      {bKey === 'thumbnail' && '(RGB Jpeg)'}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              type="button"
              style={styles.btnAcquire}
              disabled={isAcquiring || selectedBands.length === 0}
              onClick={handleAcquire}
            >
              {isAcquiring ? 'STREAMING ASSETS (ATOMIC)...' : `ACQUIRE ${selectedBands.length} ASSETS`}
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
              Target storage path: <code style={styles.code}>data/scenes/{selectedScene.external_scene_id.substring(0, 16)}.../assets/</code>
            </span>
          </div>

          {acqError && <div style={styles.errorBanner}>{acqError}</div>}

          {/* Acquisition Result Summary */}
          {acquisitionResult && (
            <div style={styles.acqResultCard}>
              <div style={styles.acqResultHeader}>
                <strong>ACQUISITION STATUS:</strong>{' '}
                <span style={styles.statusSuccess}>
                  {acquisitionResult.status.toUpperCase()} ({acquisitionResult.downloaded_assets} Downloaded, {acquisitionResult.already_present_assets} Cached, {acquisitionResult.failed_assets} Failed)
                </span>
              </div>

              <div style={styles.tableWrapper}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>ASSET</th>
                      <th style={styles.th}>STATUS</th>
                      <th style={styles.th}>SIZE</th>
                      <th style={styles.th}>SHA256 CHECKSUM</th>
                      <th style={styles.th}>LOCAL PATH</th>
                    </tr>
                  </thead>
                  <tbody>
                    {acquisitionResult.assets.map((a) => (
                      <tr key={a.asset_key}>
                        <td style={styles.tdBold}>{a.asset_key}</td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.assetStatusPill,
                              backgroundColor: a.status === 'downloaded' ? 'var(--color-primary-subtle)' : a.status === 'already_present' ? '#f0fdf4' : '#fef2f2',
                              color: a.status === 'failed' ? 'var(--color-status-offline)' : 'var(--color-primary-dark)',
                            }}
                          >
                            {a.status.toUpperCase()}
                          </span>
                        </td>
                        <td style={styles.tdMono}>
                          {a.size_bytes != null ? `${(a.size_bytes / (1024 * 1024)).toFixed(2)} MB` : '-'}
                        </td>
                        <td style={styles.tdMono}>
                          {a.sha256 ? `${a.sha256.substring(0, 16)}...` : '-'}
                        </td>
                        <td style={styles.tdMono}>{a.local_path || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    padding: '1.25rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
    borderBottom: '1px solid var(--border-color)',
    paddingBottom: '0.5rem',
  },
  title: {
    fontSize: '0.85rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
    color: 'var(--color-text-secondary)',
    margin: 0,
  },
  providerBadge: {
    fontSize: '0.7rem',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
    color: 'var(--color-primary-dark)',
    backgroundColor: 'var(--color-primary-subtle)',
    padding: '0.2rem 0.5rem',
    border: '1px solid var(--color-primary)',
  },
  desc: {
    fontSize: '0.85rem',
    color: 'var(--color-text-secondary)',
    marginBottom: '1rem',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '0.75rem',
  },
  label: {
    display: 'block',
    fontSize: '0.72rem',
    fontWeight: 700,
    color: 'var(--color-text-muted)',
    letterSpacing: '0.04em',
    marginBottom: '0.25rem',
  },
  input: {
    width: '100%',
    padding: '0.45rem 0.65rem',
    border: '1px solid var(--border-color-strong)',
    fontSize: '0.8rem',
    outline: 'none',
  },
  select: {
    width: '100%',
    padding: '0.45rem 0.65rem',
    border: '1px solid var(--border-color-strong)',
    fontSize: '0.8rem',
    backgroundColor: 'var(--color-surface)',
    cursor: 'pointer',
  },
  btnPrimary: {
    backgroundColor: 'var(--color-primary)',
    color: '#ffffff',
    border: 'none',
    padding: '0.5rem 1.25rem',
    fontWeight: 700,
    fontSize: '0.75rem',
    letterSpacing: '0.05em',
    cursor: 'pointer',
    width: '100%',
  },
  wbInfoBanner: {
    marginTop: '0.75rem',
    padding: '0.5rem 0.75rem',
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    fontSize: '0.75rem',
    display: 'flex',
    gap: '1.5rem',
    flexWrap: 'wrap',
  },
  errorBanner: {
    marginTop: '0.75rem',
    backgroundColor: '#fef2f2',
    border: '1px solid var(--color-status-offline)',
    color: 'var(--color-status-offline)',
    padding: '0.5rem 0.75rem',
    fontSize: '0.8rem',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem',
    textAlign: 'left',
  },
  th: {
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    padding: '0.5rem 0.75rem',
    fontWeight: 700,
    fontSize: '0.72rem',
    letterSpacing: '0.04em',
    color: 'var(--color-text-secondary)',
  },
  td: {
    border: '1px solid var(--border-color)',
    padding: '0.5rem 0.75rem',
    color: 'var(--color-text-primary)',
  },
  tdBold: {
    border: '1px solid var(--border-color)',
    padding: '0.5rem 0.75rem',
    fontWeight: 700,
    color: 'var(--color-text-primary)',
  },
  tdMono: {
    border: '1px solid var(--border-color)',
    padding: '0.5rem 0.75rem',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.75rem',
  },
  scorePill: {
    display: 'inline-block',
    padding: '0.15rem 0.4rem',
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    fontSize: '0.72rem',
  },
  cloudPill: {
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
  },
  assetCountPill: {
    fontSize: '0.72rem',
    color: 'var(--color-text-secondary)',
  },
  btnSelect: {
    border: '1px solid var(--border-color-strong)',
    padding: '0.3rem 0.6rem',
    fontSize: '0.7rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.03em',
  },
  acqPanel: {
    backgroundColor: 'var(--color-surface)',
    border: '2px solid var(--color-primary)',
    padding: '1.25rem',
  },
  closeBtn: {
    backgroundColor: 'transparent',
    border: '1px solid var(--border-color)',
    padding: '0.2rem 0.5rem',
    fontSize: '0.7rem',
    cursor: 'pointer',
  },
  sceneMetaRow: {
    display: 'flex',
    gap: '1.5rem',
    fontSize: '0.8rem',
    flexWrap: 'wrap',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid var(--border-color)',
  },
  bandCheckboxGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginTop: '0.4rem',
  },
  bandLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    padding: '0.3rem 0.6rem',
    border: '1px solid',
    fontSize: '0.75rem',
    cursor: 'pointer',
    userSelect: 'none',
  },
  bandHint: {
    fontSize: '0.7rem',
    color: 'var(--color-text-muted)',
  },
  btnAcquire: {
    backgroundColor: 'var(--color-accent)',
    color: '#ffffff',
    border: 'none',
    padding: '0.5rem 1.25rem',
    fontSize: '0.75rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.04em',
  },
  code: {
    fontFamily: 'var(--font-mono)',
    backgroundColor: 'var(--color-surface-subtle)',
    padding: '0.1rem 0.3rem',
    border: '1px solid var(--border-color)',
  },
  acqResultCard: {
    marginTop: '1rem',
    border: '1px solid var(--border-color)',
    padding: '0.75rem',
    backgroundColor: 'var(--color-surface-subtle)',
  },
  acqResultHeader: {
    fontSize: '0.8rem',
    marginBottom: '0.5rem',
  },
  statusSuccess: {
    color: 'var(--color-primary-dark)',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  assetStatusPill: {
    display: 'inline-block',
    padding: '0.1rem 0.35rem',
    border: '1px solid',
    fontSize: '0.7rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono)',
  },
};
