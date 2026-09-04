import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Img, Audio, staticFile, Sequence, OffthreadVideo } from 'remotion';
import React from 'react';

export const StockComparison: React.FC<{
  company_a: string;
  ticker_a: string;
  company_b: string;
  ticker_b: string;
  years: number;
  initial_investment: number;
  final_a: number;
  final_b: number;
  logo_a?: string;
  logo_b?: string;
  voiceover_audio?: string;
  part1EndFrame?: number;
  prices: { date: string; price_a: number; price_b: number }[];
}> = ({ company_a, ticker_a, company_b, ticker_b, years, initial_investment, final_a, final_b, logo_a, logo_b, voiceover_audio, part1EndFrame, prices }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  const part1End = part1EndFrame || 60; // 2 seconds by default
  const padding = 100;
  const chartWidth = width - padding * 2;
  const chartHeight = height / 2;

  // Colors
  const colorA = "#00d2ff"; // Blue
  const colorB = "#ff8c00"; // Orange

  if (!prices || prices.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const valueA = (price: number) => (initial_investment / prices[0].price_a) * price;
  const valueB = (price: number) => (initial_investment / prices[0].price_b) * price;

  const maxPrice = Math.max(...prices.map(p => Math.max(valueA(p.price_a), valueB(p.price_b))));
  const minPrice = Math.min(...prices.map(p => Math.min(valueA(p.price_a), valueB(p.price_b))));

  // Progress for chart drawing
  const chartStartFrame = part1End + 15;
  const progress = interpolate(frame, [chartStartFrame, durationInFrames - 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const visiblePointsCount = Math.max(1, Math.floor(progress * prices.length));
  const visiblePrices = prices.slice(0, visiblePointsCount);

  const getX = (index: number) => padding + (index / Math.max(1, prices.length - 1)) * chartWidth;
  const getY = (val: number) => {
    const range = maxPrice - minPrice;
    if (range === 0) return padding + chartHeight / 2;
    return padding + chartHeight - ((val - minPrice) / range) * chartHeight;
  };

  const pointsA = visiblePrices.map((p, i) => `${getX(i)},${getY(valueA(p.price_a))}`).join(' ');
  const pointsB = visiblePrices.map((p, i) => `${getX(i)},${getY(valueB(p.price_b))}`).join(' ');

  const currentA = (initial_investment / prices[0].price_a) * (visiblePrices[visiblePrices.length - 1]?.price_a || 0);
  const currentB = (initial_investment / prices[0].price_b) * (visiblePrices[visiblePrices.length - 1]?.price_b || 0);
  const currentDate = visiblePrices[visiblePrices.length - 1]?.date || '';

  const gainA = final_a - initial_investment;
  const gainB = final_b - initial_investment;

  const percentStrA = ((Math.abs(gainA) / initial_investment) * 100).toFixed(1);
  const percentDisplayA = gainA >= 0 ? `(+${percentStrA}%)` : `(-${percentStrA}%)`;

  const percentStrB = ((Math.abs(gainB) / initial_investment) * 100).toFixed(1);
  const percentDisplayB = gainB >= 0 ? `(+${percentStrB}%)` : `(-${percentStrB}%)`;

  const isUpA = currentA >= initial_investment;
  const isUpB = currentB >= initial_investment;
  const arrowA = isUpA ? '↑' : '↓';
  const arrowB = isUpB ? '↑' : '↓';
  const valColorA = isUpA ? '#0f0' : '#f00';
  const valColorB = isUpB ? '#0f0' : '#f00';

  // Slide transition calculation (slide up from Phase 1 to Phase 2)
  // Phase 1 (Logos) is at top=0 initially, moves up to -height.
  // Phase 2 (Chart) is at top=height initially, moves up to 0.
  const slideProgress = spring({
    frame: Math.max(0, frame - part1End),
    fps,
    config: { damping: 14, stiffness: 80 }
  });

  const phase1Y = interpolate(slideProgress, [0, 1], [0, -height]);
  const phase2Y = interpolate(slideProgress, [0, 1], [height, 0]);

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif', overflow: 'hidden' }}>
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}

      {/* PHASE 1: Logos and VS */}
      <AbsoluteFill style={{ transform: `translateY(${phase1Y}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <h1 style={{ fontSize: 60, marginBottom: 100 }}>What if you invested ${initial_investment} in...</h1>
        
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '80px', width: '100%', justifyContent: 'center' }}>
          {/* Company A */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '40%' }}>
            {logo_a ? (
              <Img src={staticFile(logo_a)} style={{ width: 300, height: 300, objectFit: 'contain', backgroundColor: 'white', padding: 20, borderRadius: 30 }} />
            ) : (
              <div style={{ width: 300, height: 300, backgroundColor: colorA, borderRadius: 30 }} />
            )}
            <h2 style={{ fontSize: 50, color: colorA, textAlign: 'center', marginTop: 40 }}>{company_a}</h2>
          </div>

          <h1 style={{ fontSize: 100, fontWeight: 'bold', color: '#666' }}>VS</h1>

          {/* Company B */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '40%' }}>
            {logo_b ? (
              <Img src={staticFile(logo_b)} style={{ width: 300, height: 300, objectFit: 'contain', backgroundColor: 'white', padding: 20, borderRadius: 30 }} />
            ) : (
              <div style={{ width: 300, height: 300, backgroundColor: colorB, borderRadius: 30 }} />
            )}
            <h2 style={{ fontSize: 50, color: colorB, textAlign: 'center', marginTop: 40 }}>{company_b}</h2>
          </div>
        </div>
      </AbsoluteFill>

      {/* PHASE 2: Graph */}
      <AbsoluteFill style={{ transform: `translateY(${phase2Y}px)`, padding }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: 50 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            {logo_a && <Img src={staticFile(logo_a)} style={{ width: 80, height: 80, objectFit: 'contain', backgroundColor: 'white', padding: 10, borderRadius: 15, marginBottom: 10 }} />}
            <h1 style={{ fontSize: 60, color: colorA, margin: 0 }}>{ticker_a}</h1>
            <h2 style={{ fontSize: 50, margin: 0, color: valColorA }}>${currentA.toFixed(2)} {arrowA}</h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', textAlign: 'right' }}>
            {logo_b && <Img src={staticFile(logo_b)} style={{ width: 80, height: 80, objectFit: 'contain', backgroundColor: 'white', padding: 10, borderRadius: 15, marginBottom: 10 }} />}
            <h1 style={{ fontSize: 60, color: colorB, margin: 0 }}>{ticker_b}</h1>
            <h2 style={{ fontSize: 50, margin: 0, color: valColorB }}>${currentB.toFixed(2)} {arrowB}</h2>
          </div>
        </div>
        
        <h3 style={{ fontSize: 40, color: '#aaa', textAlign: 'center', marginTop: 50 }}>{years} Year Performance</h3>
        <h3 style={{ fontSize: 30, color: '#888', textAlign: 'center' }}>{currentDate}</h3>

        <svg width={width} height={height} style={{ position: 'absolute', top: 400, left: 0 }}>
          {/* Axis */}
          <line x1={padding} y1={padding + chartHeight} x2={width - padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />
          <line x1={padding} y1={padding} x2={padding} y2={padding + chartHeight} stroke="#444" strokeWidth={2} />
          
          {/* Chart Line A */}
          <polyline points={pointsA} fill="none" stroke={colorA} strokeWidth={8} strokeLinejoin="round" />
          
          {/* Chart Line B */}
          <polyline points={pointsB} fill="none" stroke={colorB} strokeWidth={8} strokeLinejoin="round" />
        </svg>

        {progress > 0.99 && (
          <div style={{ position: 'absolute', bottom: 100, width: chartWidth, textAlign: 'center' }}>
            <h1 style={{ color: 'white', textAlign: 'center', fontSize: 50, marginBottom: 20 }}>
              Initial Investment: ${initial_investment.toFixed(2)}
            </h1>
            <h1 style={{ color: gainA >= 0 ? '#0f0' : '#f00', textAlign: 'center', fontSize: 50, margin: 10 }}>
              {ticker_a} {gainA >= 0 ? 'Gain' : 'Loss'}: {gainA >= 0 ? '+' : '-'}${Math.abs(gainA).toFixed(2)} {percentDisplayA}
            </h1>
            <h1 style={{ color: gainB >= 0 ? '#0f0' : '#f00', textAlign: 'center', fontSize: 50, margin: 10 }}>
              {ticker_b} {gainB >= 0 ? 'Gain' : 'Loss'}: {gainB >= 0 ? '+' : '-'}${Math.abs(gainB).toFixed(2)} {percentDisplayB}
            </h1>
          </div>
        )}
      </AbsoluteFill>

      {/* Outro Like & Subscribe Animation */}
      <Sequence from={part1End}>
        <OffthreadVideo muted={true} transparent={true} src={staticFile("media/video/template/like_subscribe_alpha.webm")} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
      </Sequence>

    </AbsoluteFill>
  );
};
