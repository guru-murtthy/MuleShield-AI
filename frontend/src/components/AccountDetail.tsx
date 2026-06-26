import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { Lock, Unlock, GitBranch, FileText, CheckCircle, XCircle } from 'lucide-react';
import type { ScoreResponse } from '../types';
import { RiskBadge } from './RiskBadge';
import { SHAPChart } from './SHAPChart';
import { applyAction } from '../utils/api';

interface Props {
  data: ScoreResponse;
}

export function AccountDetail({ data }: Props) {
  const [actionLoading, setActionLoading] = useState(false);
  const [freezeStatus, setFreezeStatus] = useState<string | null>(null);

  async function handleAction(action_type: string) {
    setActionLoading(true);
    try {
      const result = await applyAction(data.account_id, action_type);
      setFreezeStatus(result.status);
      toast.success(`${action_type.replace('_', ' ')} applied: ${result.status}`);
    } catch {
      toast.error('Action failed. Check API connection.');
    } finally {
      setActionLoading(false);
    }
  }

  const riskGaugeColor =
    data.risk_band === 'CRITICAL' ? '#dc2626' :
    data.risk_band === 'HIGH' ? '#f97316' :
    data.risk_band === 'MEDIUM' ? '#eab308' :
    data.risk_band === 'LOW' ? '#3b82f6' : '#9ca3af';

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900 font-mono">{data.account_id}</h2>
          <p className="text-sm text-gray-500">Model: {data.model_version ?? 'demo'}</p>
        </div>
        <RiskBadge band={data.risk_band} score={data.risk_score} size="lg" />
      </div>

      {/* Risk gauge */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>0</span><span>Risk Score</span><span>1000</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="h-3 rounded-full transition-all duration-500"
            style={{ width: `${data.risk_score / 10}%`, backgroundColor: riskGaugeColor }}
          />
        </div>
        <p className="text-center font-bold text-xl mt-1" style={{ color: riskGaugeColor }}>
          {data.risk_score} / 1000
        </p>
      </div>

      {/* Narrative */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <p className="text-sm font-semibold text-gray-700 mb-1">AI Analysis</p>
        <p className="text-sm text-gray-600 leading-relaxed">{data.narrative}</p>
      </div>

      {/* Detection Patterns */}
      {data.top_patterns.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-2">Detection Patterns</p>
          <div className="space-y-2">
            {data.top_patterns.map((p) => (
              <div key={p.pattern} className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-3 py-2">
                <span className="text-sm font-medium text-gray-700">{p.pattern.replace(/_/g, ' ')}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 bg-gray-200 rounded-full h-1.5">
                    <div className="bg-indigo-600 h-1.5 rounded-full" style={{ width: `${p.confidence * 100}%` }} />
                  </div>
                  <span className="text-xs text-gray-500 w-10 text-right">{(p.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SHAP Chart */}
      {data.shap_available && data.shap_features.length > 0 ? (
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-2">SHAP Feature Attribution</p>
          <div className="overflow-x-auto">
            <SHAPChart features={data.shap_features} width={480} height={280} />
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Red = increases risk · Blue = decreases risk
          </p>
        </div>
      ) : (
        !data.shap_available && (
          <p className="text-xs text-gray-400">SHAP unavailable for this scoring run.</p>
        )
      )}

      {/* STR Draft */}
      {data.str_draft && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-semibold text-amber-800">goAML STR Draft Ready</span>
          </div>
          <p className="text-xs text-amber-700">Status: {String(data.str_draft.status ?? 'draft')}</p>
          <button
            className="mt-2 text-xs text-amber-700 underline hover:text-amber-900"
            onClick={() => {
              const blob = new Blob([JSON.stringify(data.str_draft, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url;
              a.download = `STR_${data.account_id}.json`; a.click();
            }}
          >
            Download STR JSON
          </button>
        </div>
      )}

      {/* Actions */}
      <div>
        <p className="text-sm font-semibold text-gray-700 mb-2">Actions</p>
        {freezeStatus && (
          <div className="flex items-center gap-2 mb-3 text-sm text-green-700 bg-green-50 rounded p-2">
            <CheckCircle className="w-4 h-4" /> Action status: <strong>{freezeStatus}</strong>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          {['soft_freeze', 'hard_freeze', 'unfreeze', 'fund_trace'].map((action) => (
            <button
              key={action}
              disabled={actionLoading}
              onClick={() => handleAction(action)}
              className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {action === 'soft_freeze' && <Lock className="w-3.5 h-3.5 text-yellow-500" />}
              {action === 'hard_freeze' && <Lock className="w-3.5 h-3.5 text-red-500" />}
              {action === 'unfreeze' && <Unlock className="w-3.5 h-3.5 text-green-500" />}
              {action === 'fund_trace' && <GitBranch className="w-3.5 h-3.5 text-indigo-500" />}
              {action.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
