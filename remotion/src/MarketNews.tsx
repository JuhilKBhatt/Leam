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
  const fps = 30;
  
  const scenesWithTiming = script_json?.map((scene) => {
    // Convert whisper timestamps to frames
    const start = Math.floor((scene.start_time || 0) * fps);
    let end = Math.floor((scene.end_time || 0) * fps);
    if (end <= start) end = start + fps; // Minimum 1 sec fallback
    const duration = end - start;
    return { ...scene, start, duration };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', color: 'white', fontFamily: 'sans-serif' }}>
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}

      {scenesWithTiming?.map((scene, i) => (
        <Sequence key={i} from={scene.start} durationInFrames={scene.duration}>
          <AbsoluteFill style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            
            {/* Background Layer: B-Roll or dark fallback */}
            {scene.b_roll_video ? (
              <Video src={staticFile(scene.b_roll_video)} style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: scene.graph_image ? 0.2 : 0.6, position: 'absolute' }} muted loop />
            ) : (
              <div style={{ width: '100%', height: '100%', backgroundColor: '#222', position: 'absolute' }} />
            )}
            
            {/* Foreground Layer: Graph or Visuals Text */}
            <div style={{ zIndex: 1, padding: 40, display: 'flex', flexDirection: 'column', alignItems: 'center', width: '90%', height: '90%', justifyContent: 'center' }}>
              
              {scene.graph_image ? (
                <img src={staticFile(scene.graph_image)} style={{ width: '100%', maxHeight: '80%', objectFit: 'contain', borderRadius: 20, boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }} />
              ) : (
                <div style={{ padding: 60, backgroundColor: 'rgba(0,0,0,0.7)', borderRadius: 40, textAlign: 'center' }}>
                  <h2 style={{ fontSize: 40, marginBottom: 40, color: '#00ff99' }}>
                    {companies?.join(' • ')}
                  </h2>
                  <p style={{ fontSize: 36, lineHeight: 1.5 }}>
                    {scene.visuals}
                  </p>
                </div>
              )}
              
            </div>
          </AbsoluteFill>
        </Sequence>
      ))}

    </AbsoluteFill>
  );
};
