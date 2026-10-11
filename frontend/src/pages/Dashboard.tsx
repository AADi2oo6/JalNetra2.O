import React, { useEffect, useState } from 'react';
import {
  HealthStatus,
  StorageStatus,
  WaterBody,
  getStorageStatus,
  listWaterBodies,
  createWaterBody,
} from '../api';

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
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null);
  const [waterBodies, setWaterBodies] = useState<WaterBody[]>([]);
  const [wbCount, setWbCount] = useState<number>(0);
  const [newWbName, setNewWbName] = useState<string>('');
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const loadData = async () => {
    if (status !== 'connected') return;
    try {
      const s = await getStorageStatus();
      setStorageStatus(s);
      const wbs = await listWaterBodies(5, 0);
      setWaterBodies(wbs.items);
      setWbCount(wbs.total);
    } catch {
      // Ignored if offline
    }
  };

  useEffect(() => {
    loadData();
  }, [status]);

  const handleCreateTestBody = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWbName.trim()) return;
    setIsSubmitting(true);
    setActionMsg(null);
    try {
      const created = await createWaterBody({
        name: newWbName.trim(),
        country: 'India',
        source: 'manual',
        source_id: `test-${Date.now()}`,
      });
      setActionMsg(`Created water body: ${created.name} (ID: ${created.id.substring(0, 8)}...)`);
      setNewWbName('');
      await loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setActionMsg(`Error: ${err.message}`);
      } else {
        setActionMsg('Failed to create water body');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Overview Status Banner */}
      <section style={styles.sectionCard}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>SYSTEM STATUS & STORAGE PERSISTENCE</h2>
          <button style={styles.refreshBtn} onClick={() => { onRefresh(); loadData(); }}>
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
            <div style={styles.metricLabel}>SQLITE 3 DATABASE (ALEMBIC)</div>
            <div style={styles.metricValue}>
              {storageStatus?.database?.status === 'ok' ? 'HEALTHY (OK)' : 'OFFLINE'}
            </div>
            <div style={styles.metricDetail}>data/database/jalnetra.db</div>
          </div>

          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>CATALOG WATER BODIES</div>
            <div style={styles.metricValue}>{wbCount} RECORD(S)</div>
            <div style={styles.metricDetail}>Phase 1 Persistent Storage</div>
          </div>
        </div>
      </section>

      {/* Phase 1 Developer Persistence Controls */}
      {status === 'connected' && (
        <section style={styles.sectionCard}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>PHASE 1 PERSISTENCE TESTER</h2>
          </div>
          <p style={styles.description}>
            Add a test water body record into the local SQLite database to verify API routing, Pydantic validation, repository transactions, and persistence.
          </p>

          <form onSubmit={handleCreateTestBody} style={styles.formRow}>
            <input
              type="text"
              placeholder="Water Body Name (e.g. Sambhar Salt Lake)"
              value={newWbName}
              onChange={(e) => setNewWbName(e.target.value)}
              style={styles.input}
              disabled={isSubmitting}
            />
            <button type="submit" style={styles.submitBtn} disabled={isSubmitting}>
              {isSubmitting ? 'SAVING...' : 'INSERT RECORD'}
            </button>
          </form>

          {actionMsg && <div style={styles.actionNotice}>{actionMsg}</div>}

          {waterBodies.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <div style={styles.metricLabel}>RECENT PERSISTED WATER BODIES:</div>
              <div style={styles.tableWrapper}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>ID</th>
                      <th style={styles.th}>NAME</th>
                      <th style={styles.th}>COUNTRY</th>
                      <th style={styles.th}>SOURCE</th>
                      <th style={styles.th}>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {waterBodies.map((wb) => (
                      <tr key={wb.id}>
                        <td style={styles.tdMono}>{wb.id.substring(0, 8)}...</td>
                        <td style={styles.td}>{wb.name}</td>
                        <td style={styles.td}>{wb.country || '-'}</td>
                        <td style={styles.tdMono}>{wb.source}</td>
                        <td style={styles.td}>
                          <span style={styles.statusPill}>
                            {wb.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Architecture & Pipeline Architecture Details */}
      <section style={styles.sectionCard}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>DATA PIPELINE STORAGE SUB-DIRECTORIES</h2>
        </div>

        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>SUBSYSTEM</th>
                <th style={styles.th}>LOCAL DIRECTORY</th>
                <th style={styles.th}>FILES</th>
                <th style={styles.th}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {storageStatus?.details &&
                Object.entries(storageStatus.details).map(([key, val]) => (
                  <tr key={key}>
                    <td style={styles.td}>{key.toUpperCase()}</td>
                    <td style={styles.tdMono}>{val.path}</td>
                    <td style={styles.td}>{val.file_count}</td>
                    <td style={styles.td}>
                      <span style={styles.statusPill}>
                        {val.exists ? 'Available' : 'Missing'}
                      </span>
                    </td>
                  </tr>
                ))}
              {!storageStatus?.details && (
                <tr>
                  <td colSpan={4} style={styles.td}>
                    Connect backend to read storage directories status.
                  </td>
                </tr>
              )}
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
  formRow: {
    display: 'flex',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  input: {
    flex: 1,
    padding: '0.45rem 0.75rem',
    border: '1px solid var(--border-color-strong)',
    fontSize: '0.8rem',
    outline: 'none',
  },
  submitBtn: {
    backgroundColor: 'var(--color-primary)',
    color: '#ffffff',
    border: 'none',
    padding: '0.45rem 1rem',
    fontWeight: 700,
    fontSize: '0.75rem',
    cursor: 'pointer',
    letterSpacing: '0.04em',
  },
  actionNotice: {
    backgroundColor: 'var(--color-primary-subtle)',
    border: '1px solid var(--color-primary)',
    color: 'var(--color-primary-dark)',
    padding: '0.5rem 0.75rem',
    fontSize: '0.75rem',
    fontFamily: 'var(--font-mono)',
    marginBottom: '0.75rem',
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
