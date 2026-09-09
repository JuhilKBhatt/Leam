import { AbsoluteFill, useVideoConfig, Audio, staticFile, Sequence, Video } from 'remotion';
import React from 'react';

export const MarketNews: React.FC<{
  companies: string[];
  script_json: any[];
  voiceover_audio?: string;
}> = ({ companies, script_json, voiceover_audio }) => {
  const { durationInFrames } = useVideoConfig();

  // Calculate approximate frames per scene based on voiceover length
  const totalChars = script_json?.reduce((acc, scene) => acc + (scene.voiceover?.length || 0), 0) || 1;
  
  let currentStart = 0;
  const scenesWithTiming = script_json?.map((scene) => {
    const chars = scene.voiceover?.length || 0;
    const duration = Math.max(1, Math.floor((chars / totalChars) * durationInFrames));
    const start = currentStart;
    currentStart += duration;
    return { ...scene, start, duration };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif' }}>
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}

      {scenesWithTiming?.map((scene, i) => (
        <Sequence key={i} from={scene.start} durationInFrames={scene.duration}>
          <AbsoluteFill style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            {scene.b_roll_video ? (
              <Video src={staticFile(scene.b_roll_video)} style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.4, position: 'absolute' }} muted loop />
            ) : (
              <div style={{ width: '100%', height: '100%', backgroundColor: '#222', position: 'absolute' }} />
            )}
            
            <div style={{ zIndex: 1, padding: 80, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 40, textAlign: 'center', width: '80%' }}>
              <h1 style={{ fontSize: 60, marginBottom: 20, color: '#00d2ff' }}>
                {scene.scene}
              </h1>
              <h2 style={{ fontSize: 40, marginBottom: 40, color: '#ff8c00' }}>
                {companies?.join(' • ')}
              </h2>
              <p style={{ fontSize: 30, lineHeight: 1.5 }}>
                {scene.visuals}
              </p>
            </div>
          </AbsoluteFill>
        </Sequence>
      ))}

    </AbsoluteFill>
  );
};
