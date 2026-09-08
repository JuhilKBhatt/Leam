import { AbsoluteFill, useCurrentFrame, useVideoConfig, Audio, staticFile } from 'remotion';
import React from 'react';

export const MarketNews: React.FC<{
  companies: string[];
  script_json: any[];
  voiceover_audio?: string;
}> = ({ companies, script_json, voiceover_audio }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif', padding: 50, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}
      
      <h1 style={{ fontSize: 80, marginBottom: 50, color: '#00d2ff', textAlign: 'center' }}>
        Market News
      </h1>
      <h2 style={{ fontSize: 50, marginBottom: 50, color: '#ff8c00', textAlign: 'center' }}>
        {companies?.join(' • ')}
      </h2>

      <div style={{ fontSize: 40, textAlign: 'center', maxWidth: '80%', lineHeight: 1.5 }}>
        {script_json && script_json.length > 0 ? (
          <p>Generating news analysis for {companies?.length} companies.</p>
        ) : (
          <p>Loading market data...</p>
        )}
      </div>

    </AbsoluteFill>
  );
};
