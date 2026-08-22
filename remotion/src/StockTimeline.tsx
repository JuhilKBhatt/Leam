import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import React from 'react';

export const StockTimeline: React.FC<{
  company: string;
  ticker: string;
  years: number;
  initial_investment: number;
  gain: number;
  prices: { date: string; price: number }[];
}> = ({ company, ticker, years, initial_investment, gain, prices }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  // Draw chart
  const padding = 100;
  const chartWidth = width - padding * 2;
  const chartHeight = height / 2;

  if (!prices || prices.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const maxPrice = Math.max(...prices.map((p) => p.price));
  const minPrice = Math.min(...prices.map((p) => p.price));

  // Determine how many points to show based on frame
  // Animate the line drawing over the duration
  const progress = interpolate(frame, [0, durationInFrames - 60], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const visiblePointsCount = Math.max(1, Math.floor(progress * prices.length));
  const visiblePrices = prices.slice(0, visiblePointsCount);
  
  const currentPrice = visiblePrices[visiblePrices.length - 1]?.price || 0;
  const currentDate = visiblePrices[visiblePrices.length - 1]?.date || '';

  const getX = (index: number) => padding + (index / Math.max(1, (prices.length - 1))) * chartWidth;
  const getY = (price: number) => 
    padding + chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight;

  const points = visiblePrices.map((p, i) => `${getX(i)},${getY(p.price)}`).join(' ');

  const titleOpacity = spring({ frame, fps, config: { damping: 12 } });

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif' }}>
      <AbsoluteFill style={{ padding }}>
        <h1 style={{ fontSize: 60, opacity: titleOpacity }}>{company} ({ticker})</h1>
        <h2 style={{ fontSize: 40, color: '#aaa', marginTop: -40 }}>{years} Year Performance</h2>
        
        <div style={{ marginTop: 50, fontSize: 50 }}>
          Current Price: <span style={{ color: '#0f0' }}>${currentPrice.toFixed(2)}</span>
        </div>
        <div style={{ fontSize: 30, color: '#888' }}>{currentDate}</div>
        
        <svg width={width} height={height} style={{ position: 'absolute', top: 400, left: 0 }}>
          {/* Axis */}
          <line x1={padding} y1={padding + chartHeight} x2={width - padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />
          <line x1={padding} y1={padding} x2={padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />

          {/* Chart Line */}
          <polyline
            points={points}
            fill="none"
            stroke="#0f0"
            strokeWidth={8}
            strokeLinejoin="round"
          />
        </svg>

        {progress > 0.99 && (
          <div style={{ position: 'absolute', bottom: 200, width: chartWidth }}>
            <h1 style={{ color: 'white', textAlign: 'center', fontSize: 50 }}>
              Initial Investment: ${initial_investment.toFixed(2)}
            </h1>
            <h1 style={{ color: '#0f0', textAlign: 'center', fontSize: 60 }}>
              Total Gain: +${gain.toFixed(2)}
            </h1>
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
