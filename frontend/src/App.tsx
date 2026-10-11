import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import { Dashboard } from './pages/Dashboard';
import { DiscoveryPage } from './pages/DiscoveryPage';
import { SatellitePage } from './pages/SatellitePage';
import { MapPage } from './pages/MapPage';
import { checkHealth, HealthStatus } from './api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('map');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'offline'>('checking');
  const [healthData, setHealthData] = useState<HealthStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const data = await checkHealth();
      setHealthData(data);
      setBackendStatus('connected');
      setErrorMessage(null);
    } catch (err: unknown) {
      setHealthData(null);
      setBackendStatus('offline');
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to backend server');
      }
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    // Optional periodic poll every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return (
    <div style={styles.appContainer}>
      <Header status={backendStatus} serviceInfo={healthData} />
      <Navigation currentTab={currentTab} onTabChange={setCurrentTab} />

      <main style={styles.mainContent}>
        {currentTab === 'overview' && (
          <Dashboard
            status={backendStatus}
            healthData={healthData}
            error={errorMessage}
            onRefresh={fetchStatus}
          />
        )}
        {currentTab === 'map' && <MapPage />}
        {currentTab === 'discovery' && <DiscoveryPage />}
        {currentTab === 'satellite' && <SatellitePage />}
        {currentTab === 'catalog' && (
          <Dashboard
            status={backendStatus}
            healthData={healthData}
            error={errorMessage}
            onRefresh={fetchStatus}
          />
        )}
        {currentTab !== 'overview' && currentTab !== 'map' && currentTab !== 'discovery' && currentTab !== 'satellite' && currentTab !== 'catalog' && (
          <div style={styles.placeholderCard}>
            <h3 style={styles.placeholderTitle}>MODULE RESERVED FOR FUTURE PHASE</h3>
            <p style={styles.placeholderDesc}>
              This subsystem will be activated in subsequent releases. The core storage and API architecture are currently prepared for integration.
            </p>
          </div>
        )}
      </main>

      <footer style={styles.footer}>
        <span>JalNetra 2.0 &bull; Operational Water Body Monitoring & Remote Sensing System</span>
        <span style={styles.footerMono}>ENV: LOCAL_DEV</span>
      </footer>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  appContainer: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    backgroundColor: 'var(--color-bg)',
  },
  mainContent: {
    flex: 1,
    padding: '1.5rem',
    maxWidth: '1280px',
    width: '100%',
    margin: '0 auto',
  },
  placeholderCard: {
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--border-color)',
    padding: '2rem',
    textAlign: 'center',
  },
  placeholderTitle: {
    fontSize: '0.9rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    color: 'var(--color-accent)',
    marginBottom: '0.5rem',
  },
  placeholderDesc: {
    fontSize: '0.85rem',
    color: 'var(--color-text-secondary)',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem 1.5rem',
    backgroundColor: 'var(--color-surface)',
    borderTop: '1px solid var(--border-color)',
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
  },
  footerMono: {
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
  },
};

export default App;
