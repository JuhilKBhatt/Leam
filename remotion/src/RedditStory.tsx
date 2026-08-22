import React from 'react';
import { AbsoluteFill, Audio, Video, useVideoConfig, useCurrentFrame, staticFile } from 'remotion';

type Word = {
  word: string;
  start: number;
  end: number;
};

export const RedditStory: React.FC<{
  bgVideoPath: string;
  ttsAudioPath: string;
  musicPath?: string;
  words: Word[];
  title: string;
}> = ({ bgVideoPath, ttsAudioPath, musicPath, words, title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Find all words that should be visible (within a small window or exactly on frame)
  const activeWord = words.find((w) => {
    const startFrame = Math.round(w.start * fps);
    const endFrame = Math.round(w.end * fps);
    return frame >= startFrame && frame <= endFrame;
  });

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {bgVideoPath && (
        <Video
          src={staticFile(bgVideoPath)}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      )}
      
      {ttsAudioPath && <Audio src={staticFile(ttsAudioPath)} volume={1} />}
      {musicPath && <Audio src={staticFile(musicPath)} volume={0.15} loop />}

      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        {activeWord && (
          <div
            style={{
              fontSize: '110px',
              color: '#ffffff',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontWeight: 900,
              textTransform: 'uppercase',
              WebkitTextStroke: '4px black',
              textAlign: 'center',
              textShadow: '0 8px 24px rgba(0,0,0,0.8)',
              width: '80%',
              lineHeight: 1.2,
            }}
          >
            {activeWord.word}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
