import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Img, Audio, staticFile } from 'remotion';
import React from 'react';

export const StockTimeline: React.FC<{
  company: string;
  ticker: string;
  years: number;
  initial_investment: number;
  gain: number;
  initial_product_image?: string;
  gain_purchase_image?: string;
  voiceover_audio?: string;
  bg_music?: string;
  transition?: string;
  prices: { date: string; price: number }[];
}> = ({ company, ticker, years, initial_investment, gain, initial_product_image, gain_purchase_image, voiceover_audio, bg_music, transition, prices }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  // Phases
  const third = Math.floor(durationInFrames / 3);
  const part1End = third;
  const part2End = durationInFrames - third;
  
  const tType = transition || "fade";
  const getStyle = (phase: 1 | 2 | 3) => {
    let opacity = 1;
    let translateX = 0;
    let translateY = 0;
    let scale = 1;

    if (tType === "fade") {
      if (phase === 1) opacity = interpolate(frame, [part1End - 15, part1End], [1, 0], { extrapolateRight: 'clamp' });
      if (phase === 2) opacity = interpolate(frame, [part1End, part1End + 15, part2End - 15, part2End], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      if (phase === 3) opacity = interpolate(frame, [part2End, part2End + 15], [0, 1], { extrapolateLeft: 'clamp' });
    } else if (tType === "slide_left") {
      if (phase === 1) translateX = interpolate(frame, [part1End - 15, part1End], [0, -width], { extrapolateRight: 'clamp' });
      if (phase === 2) translateX = interpolate(frame, [part1End, part1End + 15, part2End - 15, part2End], [width, 0, 0, -width], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      if (phase === 3) translateX = interpolate(frame, [part2End, part2End + 15], [width, 0], { extrapolateLeft: 'clamp' });
    } else if (tType === "slide_up") {
      if (phase === 1) translateY = interpolate(frame, [part1End - 15, part1End], [0, -height], { extrapolateRight: 'clamp' });
      if (phase === 2) translateY = interpolate(frame, [part1End, part1End + 15, part2End - 15, part2End], [height, 0, 0, -height], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      if (phase === 3) translateY = interpolate(frame, [part2End, part2End + 15], [height, 0], { extrapolateLeft: 'clamp' });
    } else if (tType === "zoom") {
      if (phase === 1) { opacity = interpolate(frame, [part1End - 15, part1End], [1, 0], { extrapolateRight: 'clamp' }); scale = interpolate(frame, [part1End - 15, part1End], [1, 1.5], { extrapolateRight: 'clamp' }); }
      if (phase === 2) { opacity = interpolate(frame, [part1End, part1End + 15, part2End - 15, part2End], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }); scale = interpolate(frame, [part1End, part1End + 15, part2End - 15, part2End], [0.5, 1, 1, 1.5], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }); }
      if (phase === 3) { opacity = interpolate(frame, [part2End, part2End + 15], [0, 1], { extrapolateLeft: 'clamp' }); scale = interpolate(frame, [part2End, part2End + 15], [0.5, 1], { extrapolateLeft: 'clamp' }); }
    }
    
    // Hide entirely outside phases
    if (phase === 1 && frame > part1End) opacity = 0;
    if (phase === 2 && (frame < part1End || frame > part2End)) opacity = 0;
    if (phase === 3 && frame < part2End) opacity = 0;

    return { opacity, transform: `translateX(${translateX}px) translateY(${translateY}px) scale(${scale})` };
  };

  // Draw chart
  const padding = 100;
  const chartWidth = width - padding * 2;
  const chartHeight = height / 2;

  if (!prices || prices.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const maxPrice = Math.max(...prices.map((p) => p.price));
  const minPrice = Math.min(...prices.map((p) => p.price));

  const progress = interpolate(frame, [part1End + 15, part2End - 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const visiblePointsCount = Math.max(1, Math.floor(progress * prices.length));
  const visiblePrices = prices.slice(0, visiblePointsCount);
  
  const currentPrice = visiblePrices[visiblePrices.length - 1]?.price || 0;
  const currentDate = visiblePrices[visiblePrices.length - 1]?.date || '';
  const firstPrice = prices[0]?.price || 0;
  
  const isUp = currentPrice >= firstPrice;
  const lineColor = isUp ? '#0f0' : '#f00';
  const arrow = isUp ? '↑' : '↓';
  
  const sharesBought = firstPrice > 0 ? initial_investment / firstPrice : 0;
  const currentValue = sharesBought * currentPrice;

  const getX = (index: number) => padding + (index / Math.max(1, (prices.length - 1))) * chartWidth;
  const getY = (price: number) => 
    padding + chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight;

  const points = visiblePrices.map((p, i) => `${getX(i)},${getY(p.price)}`).join(' ');

  const titleOpacity = spring({ frame, fps, config: { damping: 12 } });

  const percentStr = ((Math.abs(gain) / initial_investment) * 100).toFixed(1);
  const percentDisplay = gain >= 0 ? `(+${percentStr}%)` : `(-${percentStr}%)`;

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif', overflow: 'hidden' }}>
      
      {/* Background Music */}
      {bg_music && <Audio src={staticFile(bg_music)} volume={0.05} />}
      
      {/* Voiceover */}
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}

      {/* Phase 1: Initial Product Image */}
      <AbsoluteFill style={{ ...getStyle(1), justifyContent: 'center', alignItems: 'center' }}>
        {initial_product_image && <Img src={staticFile(initial_product_image)} style={{ width: '80%', borderRadius: 40, objectFit: 'contain' }} />}
        <h1 style={{ fontSize: 70, textAlign: 'center', marginTop: 50, padding: '0 40px' }}>What if you didn't buy this?</h1>
      </AbsoluteFill>

      {/* Phase 2: Stock Graph */}
      <AbsoluteFill style={{ ...getStyle(2), padding }}>
        <h1 style={{ fontSize: 60, opacity: titleOpacity }}>{company} ({ticker})</h1>
        <h2 style={{ fontSize: 40, color: '#aaa', marginTop: -40 }}>{years} Year Performance</h2>
        
        <div style={{ marginTop: 50, fontSize: 50 }}>
          Current Price: <span style={{ color: lineColor }}>${currentPrice.toFixed(2)}</span>
        </div>
        <div style={{ fontSize: 45, marginTop: 10 }}>
          Investment Value: <span style={{ color: lineColor }}>${currentValue.toFixed(2)} {arrow}</span>
        </div>
        <div style={{ fontSize: 30, color: '#888', marginTop: 10 }}>{currentDate}</div>
        
        <svg width={width} height={height} style={{ position: 'absolute', top: 400, left: 0 }}>
          {/* Axis */}
          <line x1={padding} y1={padding + chartHeight} x2={width - padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />
          <line x1={padding} y1={padding} x2={padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />

          {/* Chart Line */}
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth={8}
            strokeLinejoin="round"
          />
        </svg>

        {progress > 0.99 && (
          <div style={{ position: 'absolute', bottom: 200, width: chartWidth }}>
            <h1 style={{ color: 'white', textAlign: 'center', fontSize: 50 }}>
              Initial Investment: ${initial_investment.toFixed(2)}
            </h1>
            <h1 style={{ color: gain >= 0 ? '#0f0' : '#f00', textAlign: 'center', fontSize: 60 }}>
              {gain >= 0 ? 'Total Gain' : 'Total Loss'}: {gain >= 0 ? '+' : '-'}${Math.abs(gain).toFixed(2)} {percentDisplay}
            </h1>
          </div>
        )}
      </AbsoluteFill>

      {/* Phase 3: Gain Purchase Image */}
      <AbsoluteFill style={{ ...getStyle(3), justifyContent: 'center', alignItems: 'center' }}>
        {gain_purchase_image && <Img src={staticFile(gain_purchase_image)} style={{ width: '80%', borderRadius: 40, objectFit: 'contain' }} />}
        <h1 style={{ fontSize: 70, textAlign: 'center', marginTop: 50, padding: '0 40px' }}>You could buy this today!</h1>
      </AbsoluteFill>

    </AbsoluteFill>
  );
};
