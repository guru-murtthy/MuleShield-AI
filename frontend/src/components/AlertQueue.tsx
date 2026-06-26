import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { Shield, AlertTriangle, Zap } from 'lucide-react';
import type { AlertItem } from '../types';
import { RiskBadge } from './RiskBadge';

interface Props {
  alerts: AlertItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

function RiskIcon({ band }: { band: string }) {
  if (band === 'CRITICAL') return <Zap className="w-4 h-4 text-red-500" />;
  if (band === 'HIGH') return <AlertTriangle className="w-4 h-4 text-orange-500" />;
  return <Shield className="w-4 h-4 text-yellow-500" />;
}

export function AlertQueue({ alerts, selectedId, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-gray-400">
        <Shield className="w-8 h-8 mb-2" />
        <p className="text-sm">No alerts found</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-100">
      {alerts.map((alert) => (
        <button
          key={alert.account_id}
          onClick={() => onSelect(alert.account_id)}
          className={clsx(
            'w-full text-left px-4 py-3 hover:bg-indigo-50 transition-colors',
            selectedId === alert.account_id && 'bg-indigo-50 border-l-4 border-indigo-600',
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RiskIcon band={alert.risk_band} />
              <span className="font-mono text-sm font-semibold text-gray-900">{alert.account_id}</span>
            </div>
            <RiskBadge band={alert.risk_band} score={alert.risk_score} size="sm" />
          </div>
          {alert.top_pattern && (
            <p className="mt-1 text-xs text-gray-500 truncate">{alert.top_pattern.replace(/_/g, ' ')}</p>
          )}
          {alert.scored_at && (
            <p className="text-xs text-gray-400 mt-0.5">
              {formatDistanceToNow(new Date(alert.scored_at), { addSuffix: true })}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
