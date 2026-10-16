import React, { useState, useEffect } from 'react';
import {
  WeatherResponse,
  WeatherConditionCode,
  WaterLevelTrendType,
  getWaterBodyWeather,
} from '../api/weather';

interface WeatherSectionProps {
  waterBodyId: string;
  waterBodyName?: string;
}

// ─── Weather SVG Icons ────────────────────────────────────────────────────────
const WeatherIcon: React.FC<{ code: WeatherConditionCode; size?: number; className?: string }> = ({
  code,
  size = 28,
  className = '',
}) => {
  switch (code) {
    case 'clear':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="12" r="5" fill="#fef08a" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      );
    case 'partly_cloudy':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M12 2v2" stroke="#eab308" />
          <path d="M4.93 4.93l1.41 1.41" stroke="#eab308" />
          <path d="M20 12h2" stroke="#eab308" />
          <path d="M19.07 4.93l-1.41 1.41" stroke="#eab308" />
          <path d="M15.5 12a4.5 4.5 0 0 0-4.5-4.5 4.48 4.48 0 0 0-1.88.42" stroke="#eab308" />
          <path d="M17.5 19H9a5 5 0 0 1-.7-9.95A6 6 0 0 1 19.8 12a3.5 3.5 0 0 1-2.3 7z" fill="#e0f2fe" />
        </svg>
      );
    case 'overcast':
    case 'fog':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" fill="#f1f5f9" />
          {code === 'fog' && <line x1="4" y1="22" x2="20" y2="22" stroke="#94a3b8" strokeWidth="2" />}
        </svg>
      );
    case 'drizzle':
    case 'rain':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25" fill="#f0f9ff" />
          <line x1="8" y1="19" x2="8" y2="21" stroke="#0ea5e9" strokeWidth="2" />
          <line x1="12" y1="17" x2="12" y2="21" stroke="#0ea5e9" strokeWidth="2" />
          <line x1="16" y1="19" x2="16" y2="21" stroke="#0ea5e9" strokeWidth="2" />
        </svg>
      );
    case 'heavy_rain':
    case 'thunderstorm':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M19 14.58A5 5 0 0 0 17 5h-1.26A8 8 0 1 0 3 13.25" fill="#e2e8f0" />
          {code === 'thunderstorm' ? (
            <polygon points="13 11 9 17 12 17 11 23 16 16 13 16 13 11" fill="#eab308" stroke="#ca8a04" strokeWidth="1" />
          ) : (
            <>
              <line x1="8" y1="16" x2="6" y2="22" stroke="#0284c7" strokeWidth="2" />
              <line x1="12" y1="16" x2="10" y2="22" stroke="#0284c7" strokeWidth="2" />
              <line x1="16" y1="16" x2="14" y2="22" stroke="#0284c7" strokeWidth="2" />
            </>
          )}
        </svg>
      );
    default:
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      );
  }
};

// ─── Helpers for trend styling ────────────────────────────────────────────────
function getTrendBadgeStyle(trend: WaterLevelTrendType) {
  switch (trend) {
    case 'LIKELY_RISING':
      return {
        bg: 'bg-emerald-50 border-emerald-300 text-emerald-800',
        badgeBg: 'bg-emerald-600 text-white',
        arrowColor: 'text-emerald-700',
      };
    case 'POSSIBLY_RISING':
      return {
        bg: 'bg-teal-50 border-teal-300 text-teal-800',
        badgeBg: 'bg-teal-600 text-white',
        arrowColor: 'text-teal-700',
      };
    case 'STABLE':
      return {
        bg: 'bg-blue-50 border-blue-200 text-blue-800',
        badgeBg: 'bg-blue-600 text-white',
        arrowColor: 'text-blue-700',
      };
    case 'POSSIBLY_FALLING':
      return {
        bg: 'bg-amber-50 border-amber-300 text-amber-800',
        badgeBg: 'bg-amber-600 text-white',
        arrowColor: 'text-amber-700',
      };
    case 'LIKELY_FALLING':
      return {
        bg: 'bg-rose-50 border-rose-300 text-rose-800',
        badgeBg: 'bg-rose-600 text-white',
        arrowColor: 'text-rose-700',
      };
    default:
      return {
        bg: 'bg-slate-50 border-slate-300 text-slate-700',
        badgeBg: 'bg-slate-600 text-white',
        arrowColor: 'text-slate-600',
      };
  }
}

function formatDayName(dateStr: string, index: number): string {
  if (index === 0) return 'Today';
  try {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export const WeatherSection: React.FC<WeatherSectionProps> = ({ waterBodyId, waterBodyName }) => {
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = async (force: boolean = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const data = await getWaterBodyWeather(waterBodyId, force);
      setWeather(data);
    } catch (err: any) {
      console.error('Weather retrieval error:', err);
      setError(err.message || 'Unable to retrieve meteorological forecast data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (waterBodyId) {
      fetchWeather(false);
    }
  }, [waterBodyId]);

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 p-6 shadow-sm mb-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🌤</span>
            <h3 className="font-semibold text-slate-800 text-base uppercase tracking-wider">
              Weather & Water Forecast
            </h3>
          </div>
          <span className="text-xs text-slate-500 animate-pulse">Connecting to Open-Meteo...</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-pulse">
          <div className="h-44 bg-slate-100 rounded-sm"></div>
          <div className="h-44 bg-slate-100 rounded-sm lg:col-span-2"></div>
        </div>
      </div>
    );
  }

  if (error || !weather) {
    return (
      <div className="bg-white border border-slate-200 p-6 shadow-sm mb-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🌤</span>
            <h3 className="font-semibold text-slate-800 text-base uppercase tracking-wider">
              Weather & Water Forecast
            </h3>
          </div>
          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
            Open-Meteo
          </span>
        </div>
        <div className="p-4 bg-slate-50 border border-slate-200 text-slate-700 text-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="font-semibold text-slate-800 mb-1">Weather Data Temporarily Unavailable</div>
            <p className="text-xs text-slate-600">{error || 'Unable to connect to the weather forecast service.'}</p>
            <p className="text-xs text-slate-500 mt-1">Satellite monitoring and spectral indicators remain fully operational.</p>
          </div>
          <button
            onClick={() => fetchWeather(true)}
            className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-medium hover:bg-slate-100 transition-colors shadow-sm"
          >
            Retry Weather
          </button>
        </div>
      </div>
    );
  }

  const { current, forecast, water_level_trend: trend, location } = weather;
  const trendStyle = getTrendBadgeStyle(trend.trend);

  // Rainfall bar chart scaling calculations
  const maxPrecip = Math.max(...forecast.map((d) => d.precipitation_mm), 10.0);

  return (
    <div className="bg-white border border-slate-200 p-6 shadow-sm mb-6">
      {/* ─── Header & Provider Attribution ─── */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-200 pb-4 mb-6 gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🌤</span>
          <div>
            <h3 className="font-bold text-slate-900 text-base tracking-wide uppercase">
              Weather & Water Forecast {waterBodyName ? `— ${waterBodyName}` : ''}
            </h3>
            <p className="text-xs text-slate-500">
              Centroid: {location.latitude.toFixed(3)}°N, {location.longitude.toFixed(3)}°E · Timezone: {location.timezone}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">
            Provider: Open-Meteo (Standard API)
          </span>
          <button
            onClick={() => fetchWeather(true)}
            disabled={refreshing}
            className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
            title="Bypass cache and refresh forecast"
          >
            <span className={refreshing ? 'animate-spin' : ''}>↻</span>
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* ─── Top Row: Current Weather & Qualitative Trend ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        {/* Panel 1: Current Weather Conditions (5 cols) */}
        <div className="lg:col-span-5 bg-slate-50 border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Current Weather Conditions
              </span>
              <span className="text-xs font-medium bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                {current.condition}
              </span>
            </div>

            <div className="flex items-center gap-4 my-2">
              <WeatherIcon code={current.condition_code} size={48} />
              <div>
                <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {current.temperature_c.toFixed(1)}°C
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Feels like {current.apparent_temperature_c.toFixed(1)}°C
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-200 text-xs">
            <div>
              <span className="text-slate-500 block">Relative Humidity</span>
              <span className="font-semibold text-slate-800">{current.humidity_percent}%</span>
            </div>
            <div>
              <span className="text-slate-500 block">Rainfall Today</span>
              <span className="font-semibold text-slate-800">{current.rain_mm.toFixed(1)} mm</span>
            </div>
            <div>
              <span className="text-slate-500 block">Cloud Cover</span>
              <span className="font-semibold text-slate-800">{current.cloud_cover_percent}%</span>
            </div>
            <div>
              <span className="text-slate-500 block">Wind Speed</span>
              <span className="font-semibold text-slate-800">
                {current.wind_speed_kmh.toFixed(1)} km/h {current.wind_direction_deg ? `(${current.wind_direction_deg}°)` : ''}
              </span>
            </div>
          </div>
        </div>

        {/* Panel 2: Rainfall-Driven Water-Level Trend (7 cols) */}
        <div className={`lg:col-span-7 border p-5 flex flex-col justify-between ${trendStyle.bg}`}>
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Rainfall-Driven Water-Level Trend
              </div>
              <span className={`text-xs px-2.5 py-0.5 font-bold uppercase tracking-wide rounded ${trendStyle.badgeBg}`}>
                {trend.trend_arrow} {trend.trend_label}
              </span>
            </div>

            <p className="text-xs text-slate-800 leading-relaxed font-medium mb-3">
              {trend.reason}
            </p>

            <div className="bg-white/80 border border-slate-200/80 p-3 rounded-sm mb-3">
              <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500 block mb-1">
                Expected Environmental Response
              </span>
              <p className="text-xs text-slate-800 leading-relaxed">
                {trend.expected_response}
              </p>
            </div>
          </div>

          <div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t border-slate-200/60 text-xs mb-3">
              <div>
                <span className="text-slate-500 block text-[11px]">Rainfall Impact</span>
                <span className="font-semibold text-slate-800">{trend.rainfall_impact}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Dryness Impact</span>
                <span className="font-semibold text-slate-800">{trend.dryness_impact}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">7-Day Forecast Rain</span>
                <span className="font-semibold text-slate-800">{trend.forecast_rainfall_7d_mm} mm</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Trend Confidence</span>
                <span className="font-semibold text-slate-800">{trend.confidence}</span>
              </div>
            </div>

            {trend.satellite_baseline_detail && (
              <div className="text-[11px] text-slate-600 bg-white/60 p-2 border border-slate-200/60 rounded-sm mb-2">
                <span className="font-semibold">Satellite Baseline: </span>
                {trend.satellite_baseline_detail}
              </div>
            )}

            <div className="text-[10px] text-slate-500 italic">
              ℹ️ {trend.disclaimer}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Middle Section: 7-Day Forecast Timeline ─── */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            7-Day Meteorological Forecast
          </span>
          <span className="text-[11px] text-slate-500">Scroll horizontally on smaller screens</span>
        </div>

        <div className="overflow-x-auto pb-2">
          <div className="grid grid-cols-7 gap-2 min-w-[700px]">
            {forecast.map((day, idx) => (
              <div
                key={day.date}
                className={`p-3 border text-center flex flex-col items-center justify-between transition-colors ${
                  idx === 0
                    ? 'bg-blue-50/50 border-blue-300 shadow-xs'
                    : 'bg-slate-50 border-slate-200 hover:bg-slate-100/60'
                }`}
              >
                <div className="text-[11px] font-bold text-slate-700 mb-1">
                  {formatDayName(day.date, idx)}
                </div>

                <div className="my-1.5">
                  <WeatherIcon code={day.condition_code} size={28} />
                </div>

                <div className="text-xs font-semibold text-slate-800">
                  {Math.round(day.temp_max_c)}° / <span className="text-slate-500 font-normal">{Math.round(day.temp_min_c)}°</span>
                </div>

                <div className="mt-2 text-[11px] font-mono text-slate-700">
                  {day.precipitation_mm > 0 ? (
                    <span className="text-blue-600 font-medium">{day.precipitation_mm.toFixed(1)} mm</span>
                  ) : (
                    <span className="text-slate-400">0 mm</span>
                  )}
                </div>

                <div className="text-[10px] text-slate-500 mt-0.5">
                  {day.precipitation_probability_max != null ? `${day.precipitation_probability_max}% rain` : '—'}
                </div>

                <div className="text-[10px] text-slate-600 truncate max-w-[85px] mt-1" title={day.condition}>
                  {day.condition}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Bottom Section: Forecast Rainfall Visualization ─── */}
      <div className="bg-slate-50 border border-slate-200 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-800 block">
              Forecast Rainfall Trend (7-Day Projection)
            </span>
            <span className="text-xs text-slate-500">
              Daily accumulated precipitation in millimeters (mm)
            </span>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <div>
              <span className="text-slate-500 block text-[11px]">7-Day Total</span>
              <span className="font-bold text-blue-700 text-sm">{trend.forecast_rainfall_7d_mm} mm</span>
            </div>
            {trend.wettest_day_date && (
              <div>
                <span className="text-slate-500 block text-[11px]">Wettest Day</span>
                <span className="font-semibold text-slate-800">
                  {trend.wettest_day_rainfall_mm} mm ({trend.wettest_day_date})
                </span>
              </div>
            )}
            <div>
              <span className="text-slate-500 block text-[11px]">Rain Probability</span>
              <span className="font-semibold text-slate-800">{trend.rain_probability_label}</span>
            </div>
          </div>
        </div>

        {/* SVG Bar Chart */}
        <div className="w-full bg-white border border-slate-200 p-4 rounded-sm">
          <svg viewBox="0 0 700 130" className="w-full h-32 overflow-visible">
            {/* Grid lines */}
            <line x1="40" y1="20" x2="680" y2="20" stroke="#f1f5f9" strokeWidth="1" />
            <line x1="40" y1="60" x2="680" y2="60" stroke="#f1f5f9" strokeWidth="1" />
            <line x1="40" y1="100" x2="680" y2="100" stroke="#e2e8f0" strokeWidth="1" />

            {/* Y-axis labels */}
            <text x="32" y="24" textAnchor="end" fontSize="10" fill="#94a3b8" fontFamily="monospace">
              {maxPrecip.toFixed(0)}
            </text>
            <text x="32" y="64" textAnchor="end" fontSize="10" fill="#94a3b8" fontFamily="monospace">
              {(maxPrecip / 2).toFixed(0)}
            </text>
            <text x="32" y="104" textAnchor="end" fontSize="10" fill="#94a3b8" fontFamily="monospace">
              0
            </text>

            {/* Bars */}
            {forecast.map((day, idx) => {
              const x = 50 + idx * 90;
              const barWidth = 44;
              const barHeight = (day.precipitation_mm / maxPrecip) * 80;
              const y = 100 - barHeight;
              const hasRain = day.precipitation_mm > 0;

              return (
                <g key={day.date}>
                  {/* Bar */}
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={Math.max(barHeight, 2)}
                    fill={hasRain ? '#0284c7' : '#cbd5e1'}
                    rx="1"
                    className="transition-all hover:opacity-80"
                  />
                  {/* Precipitation Value Label */}
                  {hasRain && (
                    <text
                      x={x + barWidth / 2}
                      y={Math.max(y - 4, 12)}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#0369a1"
                      fontWeight="600"
                      fontFamily="monospace"
                    >
                      {day.precipitation_mm.toFixed(1)}
                    </text>
                  )}
                  {/* Date label */}
                  <text
                    x={x + barWidth / 2}
                    y="118"
                    textAnchor="middle"
                    fontSize="10"
                    fill="#475569"
                    fontWeight="500"
                  >
                    {formatDayName(day.date, idx)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
};
