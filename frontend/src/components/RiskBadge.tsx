import React from 'react';
import clsx from 'clsx';
import { RISK_BAND_COLORS, RISK_BAND_DOT } from '../types';

interface Props {
  band: string;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({ band, score, size = 'md' }: Props) {
  const colorClass = RISK_BAND_COLORS[band] ?? 'bg-gray-100 text-gray-700';
  const dotClass = RISK_BAND_DOT[band] ?? 'bg-gray-400';

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-semibold rounded-full',
        colorClass,
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-1 text-sm',
        size === 'lg' && 'px-3 py-1.5 text-base',
      )}
    >
      <span className={clsx('rounded-full', dotClass, size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2')} />
      {band}
      {score !== undefined && <span className="ml-1 opacity-75">({score})</span>}
    </span>
  );
}
