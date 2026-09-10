import React from 'react';
import { AbsoluteFill, Img, spring, useCurrentFrame, useVideoConfig, Video } from 'remotion';

export const TitleOverlay: React.FC<{ text: string; subtext?: string }> = ({ text, subtext }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const scale = spring({ fps, frame, config: { damping: 12 } });
  
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ transform: `scale(${scale})`, backgroundColor: 'rgba(0,0,0,0.8)', padding: '60px 100px', borderRadius: 40, textAlign: 'center' }}>
        <h1 style={{ fontSize: 80, color: '#00ff99', margin: 0 }}>{text}</h1>
        {subtext && <h2 style={{ fontSize: 50, color: '#ffffff', marginTop: 20 }}>{subtext}</h2>}
      </div>
    </AbsoluteFill>
  );
};

export const FigureShow: React.FC<{ image_url?: string; name: string }> = ({ image_url, name }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = spring({ fps, frame, config: { damping: 20 } });
  const translateY = spring({ fps, frame, config: { damping: 15 }, from: 100, to: 0 });
  
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity, transform: `translateY(${translateY}px)` }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.7)', padding: 40, borderRadius: 30 }}>
        {image_url && <Img src={image_url} style={{ width: 400, height: 400, objectFit: 'cover', borderRadius: 200, border: '10px solid #00d2ff' }} />}
        <h2 style={{ fontSize: 60, color: '#00d2ff', marginTop: 30 }}>{name}</h2>
      </div>
    </AbsoluteFill>
  );
};

export const FigureQuote: React.FC<{ image_url?: string; name: string; quote: string }> = ({ image_url, name, quote }) => {
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.85)', padding: 60, borderRadius: 40, maxWidth: '80%' }}>
        {image_url && <Img src={image_url} style={{ width: 300, height: 300, objectFit: 'cover', borderRadius: 150, marginRight: 60 }} />}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <p style={{ fontSize: 45, color: '#fff', fontStyle: 'italic' }}>"{quote}"</p>
          <p style={{ fontSize: 35, color: '#ff8c00', marginTop: 20, fontWeight: 'bold' }}>- {name}</p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const ObjectShow: React.FC<{ image_url?: string; object_name: string }> = ({ image_url, object_name }) => {
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.1)', padding: 50, borderRadius: 40, backdropFilter: 'blur(20px)' }}>
        {image_url && <Img src={image_url} style={{ width: 600, height: 400, objectFit: 'contain', borderRadius: 20 }} />}
        <h2 style={{ fontSize: 70, color: '#fff', marginTop: 30, textShadow: '0px 5px 10px rgba(0,0,0,0.5)' }}>{object_name}</h2>
      </div>
    </AbsoluteFill>
  );
};

export const NewsClipping: React.FC<{ headline: string; source: string; date: string; image_url?: string }> = ({ headline, source, date, image_url }) => {
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ backgroundColor: '#fff', color: '#000', padding: 60, borderRadius: 20, maxWidth: '80%', boxShadow: '0px 20px 50px rgba(0,0,0,0.5)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '4px solid #000', paddingBottom: 20, marginBottom: 40 }}>
          <span style={{ fontSize: 35, fontWeight: 'bold', fontFamily: 'serif' }}>{source}</span>
          <span style={{ fontSize: 30, fontFamily: 'serif' }}>{date}</span>
        </div>
        <h1 style={{ fontSize: 65, fontFamily: 'serif', lineHeight: 1.2 }}>{headline}</h1>
        {image_url && <Img src={image_url} style={{ width: '100%', height: 400, objectFit: 'cover', marginTop: 40, filter: 'grayscale(100%)' }} />}
      </div>
    </AbsoluteFill>
  );
};

export const AnimatedGraphShow: React.FC<{ graph_video?: string }> = ({ graph_video }) => {
  if (!graph_video) return null;
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
       <div style={{ width: '90%', height: '80%', borderRadius: 40, overflow: 'hidden', boxShadow: '0px 20px 50px rgba(0,0,0,0.8)' }}>
          <Video src={graph_video} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted />
       </div>
    </AbsoluteFill>
  );
};

export const MetricCard: React.FC<{ metric_name: string; metric_value: string }> = ({ metric_name, metric_value }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ fps, frame, config: { damping: 15 } });
  
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ transform: `scale(${scale})`, backgroundColor: 'rgba(255,255,255,0.9)', padding: '50px 80px', borderRadius: 30, textAlign: 'center', boxShadow: '0px 20px 40px rgba(0,0,0,0.5)' }}>
        <h3 style={{ fontSize: 40, color: '#555', margin: 0, textTransform: 'uppercase', letterSpacing: 2 }}>{metric_name}</h3>
        <h1 style={{ fontSize: 100, color: '#00d2ff', margin: '20px 0 0 0', fontWeight: 'bold' }}>{metric_value}</h1>
      </div>
    </AbsoluteFill>
  );
};

export const BulletList: React.FC<{ title: string; bullets: string[] }> = ({ title, bullets }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const translateY = spring({ fps, frame, config: { damping: 20 }, from: 100, to: 0 });
  
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'flex-start', paddingLeft: '10%' }}>
      <div style={{ transform: `translateY(${translateY}px)`, backgroundColor: 'rgba(0,0,0,0.85)', padding: '60px 80px', borderRadius: 40, width: '70%' }}>
        <h2 style={{ fontSize: 60, color: '#00ff99', margin: '0 0 40px 0', borderBottom: '4px solid #333', paddingBottom: 20 }}>{title}</h2>
        <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
          {bullets?.map((bullet, idx) => (
            <li key={idx} style={{ fontSize: 45, color: '#fff', marginBottom: 30, display: 'flex', alignItems: 'center' }}>
              <span style={{ color: '#00d2ff', marginRight: 20, fontSize: 50 }}>•</span> {bullet}
            </li>
          ))}
        </ul>
      </div>
    </AbsoluteFill>
  );
};
