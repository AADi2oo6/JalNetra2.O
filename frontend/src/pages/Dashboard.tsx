import React from 'react';
import { HealthStatus } from '../api';

interface DashboardProps {
  status: 'connected' | 'offline' | 'checking';
  healthData: HealthStatus | null;
  error: string | null;
  onRefresh: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  status,
  healthData,
  error,
  onRefresh,
}) => {
  return (
    <div style={styles.container}>
      {/* Overview Status Banner */}
      <section style={styles.sectionCard}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>SYSTEM STATUS & CONNECTIVITY</h2>
          <button style={styles.refreshBtn} onClick={onRefresh}>
            CHECK STATUS
          </button>
        </div>

        <div style={styles.grid}>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>BACKEND API SERVICE</div>
            <div
              style={{
                ...styles.metricValue,
                color:
                  status === 'connected'
                    ? 'var(--color-primary)'
                    : status === 'checking'
                    ? 'var(--color-text-secondary)'
                    : 'var(--color-status-offline)',
              }}
            >
              {status === 'connected' ? 'ONLINE / CONNECTED' : status === 'checking' ? 'PROBING...' : 'OFFLINE'}
            </div>
            <div style={styles.metricDetail}>
              {status === 'connected'
                ? `${healthData?.service} (v${healthData?.version})`
                : error || 'Service unreachable on configured endpoint'}
            </div>
          </div>

          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>LOCAL STORAGE DATABASE</div>
            <div style={styles.metricValue}>SQLITE 3</div>
            <div style={styles.metricDetail}>data/database/jalnetra.db</div>
          </div>

          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>CURRENT MILESTONE</div>
            <div style={styles.metricValue}>PHASE 0</div>
            <div style={styles.metricDetail}>Core Development Foundation Established</div>
          </div>
        </div>
      </section>

      {/* Architecture & Pipeline Architecture Details */}
      <section style={styles.sectionCard}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>DATA PIPELINE ARCHITECTURE (FOUNDATION)</h2>
        </div>
        <p style={styles.description}>
          JalNetra 2.0 operates a multi-stage geospatial water monitoring pipeline. Local storage
          manifests and directory structures are initialized to ensure stable offline-first
          and local processing before cloud or satellite synchronization.
        </p>

        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>SUBSYSTEM</th>
                <th style={styles.th}>LOCAL DIRECTORY</th>
                <th style={styles.th}>PHASE</th>
                <th style={styles.th}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={styles.td}>Spatial Water-Body Catalog</td>
                <td style={styles.tdMono}>data/water_bodies/</td>
                <td style={styles.td}>Phase 1</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
              <tr>
                <td style={styles.td}>Raw Satellite Scenes (Sentinel-2)</td>
                <td style={styles.tdMono}>data/scenes/</td>
                <td style={styles.td}>Phase 2</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
              <tr>
                <td style={styles.td}>Spectral & Mask Processed Products</td>
                <td style={styles.tdMono}>data/processed/</td>
                <td style={styles.td}>Phase 3</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
              <tr>
                <td style={styles.td}>Map Tiles Cache</td>
                <td style={styles.tdMono}>data/tiles/</td>
                <td style={styles.td}>Phase 3</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
              <tr>
                <td style={styles.td}>Analytical & Report Exports</td>
                <td style={styles.tdMono}>data/exports/</td>
                <td style={styles.td}>Phase 4</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
              <tr>
                <td style={styles.td}>Sync Manifests & Checkpoints</td>
                <td style={styles.tdMono}>data/manifests/</td>
                <td style={styles.td}>Phase 1-4</td>
                <td style={styles.td}><span style={styles.statusPill}>Initialized</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  sectionCard: {
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    padding: '1.25rem',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
    borderBottom: '1px solid var(--border-color)',
    paddingBottom: '0.5rem',
  },
  sectionTitle: {
    fontSize: '0.85rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
    color: 'var(--color-text-secondary)',
    margin: 0,
  },
  description: {
    fontSize: '0.85rem',
    color: 'var(--color-text-secondary)',
    marginBottom: '1rem',
  },
  refreshBtn: {
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color-strong)',
    color: 'var(--color-text-primary)',
    padding: '0.3rem 0.75rem',
    fontSize: '0.75rem',
    fontWeight: 600,
    cursor: 'pointer',
    letterSpacing: '0.03em',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: '1rem',
  },
  metricCard: {
    backgroundColor: 'var(--color-surface-subtle)',
    border: '1px solid var(--border-color)',
    padding: '1rem',
  },
  metricLabel: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: 'var(--color-text-muted)',
    letterSpacing: '0.05em',
    marginBottom: '0.25rem',
  },
  metricValue: {
    fontSize: '1.15rem',
    fontWeight: 800,
    letterSpacing: '0.02em',
    marginBottom: '0.25rem',
  },
  metricDetail: {
    fontSize: '0.75rem',
    color: 'var(--color-text-secondary)',
    fontFamily: 'var(--font-mono)',
    wordBreak: 'break-all',
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
  tdMono: {
    border: '1px solid var(--border-color)',
    padding: '0.5rem 0.75rem',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.75rem',
    color: 'var(--color-text-secondary)',
  },
  statusPill: {
    display: 'inline-block',
    fontSize: '0.7rem',
    fontWeight: 600,
    color: 'var(--color-primary-dark)',
    backgroundColor: 'var(--color-primary-subtle)',
    padding: '0.15rem 0.4rem',
    border: '1px solid var(--color-primary)',
  },
};
