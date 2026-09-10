import { AbsoluteFill, useVideoConfig, Audio, staticFile, Sequence, Video } from 'remotion';
import React from 'react';
import { TitleOverlay, FigureShow, FigureQuote, ObjectShow, NewsClipping, AnimatedGraphShow, MetricCard, BulletList } from './elements/VideoElements';

export const MarketNews: React.FC<{
  companies: string[];
  background_videos: string[];
  info_layer: any[];
  voiceover_audio?: string;
}> = ({ companies, background_videos, info_layer, voiceover_audio }) => {
  const { fps, durationInFrames } = useVideoConfig();

  // Background videos loop sequentially if there are multiple
  const bgDuration = background_videos && background_videos.length > 0 
    ? Math.floor(durationInFrames / background_videos.length)
    : durationInFrames;

  const elementsWithTiming = info_layer?.map((el) => {
    const start = Math.floor((el.start_time || 0) * fps);
    let end = Math.floor((el.end_time || 0) * fps);
    if (end <= start) end = start + fps;
    const duration = end - start;
    return { ...el, start, duration };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#111', fontFamily: 'sans-serif' }}>
      
      {/* Background B-Roll Layer */}
      {background_videos && background_videos.map((bg, i) => (
         <Sequence key={`bg-${i}`} from={i * bgDuration} durationInFrames={bgDuration}>
            <Video src={staticFile(bg)} style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute' }} muted loop />
         </Sequence>
      ))}
      {!background_videos?.length && <AbsoluteFill style={{ backgroundColor: '#111' }} />}

      {/* Voiceover */}
      {voiceover_audio && <Audio src={staticFile(voiceover_audio)} />}

      {/* Info Layer / Editor Elements */}
      {elementsWithTiming?.map((el, i) => (
        <Sequence key={`info-${i}`} from={el.start} durationInFrames={el.duration}>
            {el.type === 'Title' && <TitleOverlay text={el.text} subtext={el.subtext} />}
            {el.type === 'FigureShow' && <FigureShow name={el.name} image_url={el.image_url ? staticFile(el.image_url) : undefined} />}
            {el.type === 'FigureQuote' && <FigureQuote name={el.name} quote={el.quote} image_url={el.image_url ? staticFile(el.image_url) : undefined} />}
            {el.type === 'ObjectShow' && <ObjectShow object_name={el.object_name} image_url={el.image_url ? staticFile(el.image_url) : undefined} />}
            {el.type === 'NewsClipping' && <NewsClipping headline={el.headline} source={el.source} date={el.date} image_url={el.image_url ? staticFile(el.image_url) : undefined} />}
            {el.type === 'AnimatedGraph' && <AnimatedGraphShow graph_video={el.graph_video ? staticFile(el.graph_video) : undefined} />}
            {el.type === 'MetricCard' && <MetricCard metric_name={el.metric_name} metric_value={el.metric_value} />}
            {el.type === 'BulletList' && <BulletList title={el.title} bullets={el.bullets} />}
        </Sequence>
      ))}

    </AbsoluteFill>
  );
};
