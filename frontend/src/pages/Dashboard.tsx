import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Shield, RefreshCw, WifiOff, Activity } from 'lucide-react';
import { AlertQueue } from '../components/AlertQueue';
import { AccountDetail } from '../components/AccountDetail';
import { fetchAlerts, fetchHealth, scoreAccount } from '../utils/api';
import type { ScoreResponse } from '../types';

const REFRESH_INTERVAL = 30_000; // 30 seconds

export function Dashboard() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<ScoreResponse | null>(null);
  const [bandFilter, setBandFilter] = useState<string>('');
  const [detailLoading, setDetailLoading] = useState(false);

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  });

  const { data: alertsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['alerts', bandFilter],
    queryFn: () => fetchAlerts(1, 50, bandFilter || undefined),
    refetchInterval: REFRESH_INTERVAL,
  });

  const handleSelectAccount = useCallback(async (accountId: string) => {
    setSelectedId(accountId);
    const existing = alertsData?.items.find((a) => a.account_id === accountId);
    if (!existing) return;

    // Request a score to get full detail (using zero vector as placeholder for demo)
    setDetailLoading(true);
    try {
      const detail = await scoreAccount(accountId, new Array(100).fill(0));
      setSelectedDetail(detail);
    } catch {
      toast.error('Failed to load account details');
    } finally {
      setDetailLoading(false);
    }
  }, [alertsData]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <Shield className="w-7 h-7 text-indigo-600" />
          <div>
            <h1 className="text-lg font-bold text-gray-900">MuleShield AI</h1>
            <p className="text-xs text-gray-500">Fraud Investigator Dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {health ? (
            <span className={`flex items-center gap-1.5 text-sm ${health.models_loaded ? 'text-green-600' : 'text-amber-600'}`}>
              <Activity className="w-4 h-4" />
              {health.models_loaded ? `${health.model_count} models loaded` : 'No models — run training'}
            </span>
          ) : isError ? (
            <span className="flex items-center gap-1 text-sm text-red-500">
              <WifiOff className="w-4 h-4" /> API offline
            </span>
          ) : null}
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </header>

      {/* API offline banner */}
      {isError && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-2 flex items-center gap-2 text-sm text-red-700">
          <WifiOff className="w-4 h-4" />
          Cannot reach the Scoring API. Showing last loaded data.
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Alert Queue */}
        <aside className="w-96 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Alert Queue</h2>
              <p className="text-xs text-gray-400">{alertsData?.total ?? 0} alerts · auto-refreshes every 30s</p>
            </div>
            <select
              value={bandFilter}
              onChange={(e) => setBandFilter(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-600"
            >
              <option value="">All bands</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
          <div className="overflow-y-auto flex-1">
            <AlertQueue
              alerts={alertsData?.items ?? []}
              selectedId={selectedId}
              onSelect={handleSelectAccount}
              loading={isLoading}
            />
          </div>
        </aside>

        {/* Right: Account Detail */}
        <main className="flex-1 overflow-y-auto">
          {detailLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
            </div>
          ) : selectedDetail ? (
            <AccountDetail data={selectedDetail} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-3">
              <Shield className="w-16 h-16 opacity-20" />
              <p className="text-lg font-medium">Select an alert to investigate</p>
              <p className="text-sm">Click any account in the alert queue on the left</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
