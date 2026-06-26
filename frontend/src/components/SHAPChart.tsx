import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { SHAPFeature } from '../types';

interface Props {
  features: SHAPFeature[];
  width?: number;
  height?: number;
}

export function SHAPChart({ features, width = 500, height = 300 }: Props) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current || features.length === 0) return;
    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();

    const margin = { top: 16, right: 40, bottom: 16, left: 150 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const top10 = features.slice(0, 10);
    const maxAbs = d3.max(top10, (d) => Math.abs(d.shap_value)) ?? 0.1;

    const x = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([0, w]);
    const y = d3.scaleBand()
      .domain(top10.map((d) => d.name))
      .range([0, h])
      .padding(0.3);

    const g = svg
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Zero line
    g.append('line')
      .attr('x1', x(0)).attr('x2', x(0))
      .attr('y1', 0).attr('y2', h)
      .attr('stroke', '#d1d5db')
      .attr('stroke-dasharray', '4');

    // Bars
    g.selectAll('.bar')
      .data(top10)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', (d) => (d.shap_value >= 0 ? x(0) : x(d.shap_value)))
      .attr('y', (d) => y(d.name)!)
      .attr('width', (d) => Math.abs(x(d.shap_value) - x(0)))
      .attr('height', y.bandwidth())
      .attr('rx', 3)
      .attr('fill', (d) => (d.shap_value >= 0 ? '#ef4444' : '#3b82f6'))
      .attr('opacity', 0.85);

    // Labels
    g.selectAll('.label')
      .data(top10)
      .join('text')
      .attr('class', 'label')
      .attr('x', -4)
      .attr('y', (d) => y(d.name)! + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', 'end')
      .attr('font-size', '11px')
      .attr('fill', '#374151')
      .text((d) => d.name.slice(0, 16));

    // Value labels
    g.selectAll('.val')
      .data(top10)
      .join('text')
      .attr('class', 'val')
      .attr('x', (d) => (d.shap_value >= 0 ? x(d.shap_value) + 4 : x(d.shap_value) - 4))
      .attr('y', (d) => y(d.name)! + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', (d) => (d.shap_value >= 0 ? 'start' : 'end'))
      .attr('font-size', '10px')
      .attr('fill', '#6b7280')
      .text((d) => d.shap_value.toFixed(3));
  }, [features, width, height]);

  return <svg ref={ref} />;
}
