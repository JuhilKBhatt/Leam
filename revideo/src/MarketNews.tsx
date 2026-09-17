import {makeScene2D, Video, Audio, Txt, Img, Rect, Layout} from '@revideo/2d';
import {createRef, createSignal, waitFor, useScene, all, tween, easeInOutCubic, spawn, usePlayback} from '@revideo/core';
import {loadLexendFont} from './utils/font';

export default makeScene2D('MarketNews', function* (view) {
    const playback = usePlayback();
    const variables = useScene().variables;

    const scenes = variables.get('scenes', [] as any[])();
    const background_videos = variables.get('background_videos', [] as string[])();
    const rawInfoLayer = variables.get('info_layer', [] as any[])();
    const voiceover_audio = variables.get('voiceover_audio', '')();
    const bg_music = variables.get('bg_music', '')();
    const durationInFrames = variables.get('durationInFrames', 900)();
    const fps = 30;
    const totalDurationSec = durationInFrames / fps;
    const width = 1920;
    const height = 1080;
    const frameMargin = 120; // Safe margin from video frame edges
    const maxContentWidth = width - frameMargin * 2; // 1680px safe area

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (!p) return '';
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };

    // Load Lexend font and set as scene default
    yield loadLexendFont(getAbs);
    view.fontFamily('Lexend');

    // Audio mixing: voiceover + background music
    if (voiceover_audio) {
        view.add(<Audio src={getAbs(voiceover_audio)} play={true} volume={1} />);
    }
    if (bg_music) {
        view.add(<Audio src={getAbs(bg_music)} play={true} volume={0.07} />);
    }

    // 1. Build Background Video Timeline
    interface BgClip {
        video: string;
        startTime: number;
    }
    const bgClips: BgClip[] = [];

    if (scenes && scenes.length > 0) {
        for (const sc of scenes) {
            if (sc.b_roll_video) {
                bgClips.push({
                    video: sc.b_roll_video,
                    startTime: sc.start_time !== undefined ? Number(sc.start_time) : 0,
                });
            }
        }
    } else if (background_videos && background_videos.length > 0) {
        const slotDuration = totalDurationSec / background_videos.length;
        background_videos.forEach((vid, i) => {
            bgClips.push({
                video: vid,
                startTime: i * slotDuration,
            });
        });
    }

    // Background Container
    const bgVideoRefs = bgClips.map(() => createRef<Video>());
    view.add(
        <Rect width="100%" height="100%" fill="#0a0e17">
            {bgClips.map((bg, idx) => (
                <Video
                    ref={bgVideoRefs[idx]}
                    src={getAbs(bg.video)}
                    play={true}
                    loop={true}
                    volume={0}
                    size={['100%', '100%']}
                    opacity={idx === 0 ? 1 : 0}
                />
            ))}
            {/* Cinematic dark tint overlay for readability */}
            <Rect width="100%" height="100%" fill="rgba(10, 14, 23, 0.5)" />
        </Rect>
    );

    // Spawn concurrent background switcher task
    if (bgClips.length > 1) {
        spawn(function* () {
            for (let i = 0; i < bgClips.length; i++) {
                const currentClip = bgClips[i];
                const nextClip = bgClips[i + 1];

                if (i > 0 && bgVideoRefs[i]()) {
                    yield* all(
                        bgVideoRefs[i]().opacity(1, 0.6, easeInOutCubic),
                        bgVideoRefs[i - 1]() ? bgVideoRefs[i - 1]().opacity(0, 0.6, easeInOutCubic) : waitFor(0.6)
                    );
                }

                if (nextClip) {
                    const waitDuration = Math.max(0.1, nextClip.startTime - currentClip.startTime - (i > 0 ? 0.6 : 0));
                    yield* waitFor(waitDuration);
                }
            }
        });
    }

    // 2. Build Unified Elements Timeline
    let elements: any[] = [];
    if (scenes && scenes.length > 0) {
        for (const sc of scenes) {
            if (Array.isArray(sc.elements)) {
                for (const el of sc.elements) {
                    const elStart = el.start_time !== undefined ? Number(el.start_time) : Number(sc.start_time || 0);
                    const elEnd = el.end_time !== undefined ? Number(el.end_time) : Number(sc.end_time || elStart + 4);
                    elements.push({
                        ...el,
                        start_time: elStart,
                        end_time: elEnd,
                    });
                }
            }
        }
    }
    if (rawInfoLayer && rawInfoLayer.length > 0) {
        elements = [...elements, ...rawInfoLayer];
    }

    elements.sort((a, b) => (a.start_time || 0) - (b.start_time || 0));

    // OVERLAP PROTECTION: Enforce strictly non-overlapping timeline with clean gaps
    let lastElementEnd = 0;
    for (const el of elements) {
        let start = Number(el.start_time) || 0;
        let end = Number(el.end_time) || (start + 4.0);

        // Ensure at least 0.5s pause after previous element
        if (start < lastElementEnd + 0.5) {
            start = lastElementEnd + 0.5;
        }
        // Ensure minimum display duration
        const minDuration = el.type === 'AnimatedGraph' ? 5.5 : 3.5;
        if (end - start < minDuration) {
            end = start + minDuration;
        }
        el.start_time = start;
        el.end_time = end;
        lastElementEnd = end;

        if (el.type === 'AnimatedGraph') {
            console.log(`[MarketNews-Revideo] [Graph] Scheduled AnimatedGraph: ticker="${el.ticker}", title="${el.title || ''}", video="${el.graph_video}", resolvedSrc="${getAbs(el.graph_video)}", window=[${el.start_time}s -> ${el.end_time}s] (duration=${(el.end_time - el.start_time).toFixed(2)}s)`);
        }
    }

    // Pre-mount all overlay element cards upfront so Revideo pre-loads all images and video decoders at frame 0
    const overlayLayer = createRef<Rect>();
    const elementRefs = elements.map(() => createRef<Rect>());
    const graphFrameSignals: Record<number, any> = {};

    function renderElementNode(el: any, index: number) {
        const nodeRef = elementRefs[index];

        if (el.type === 'Title') {
            const cardPadding = 60;
            const innerWidth = Math.min(1400, maxContentWidth - cardPadding * 2);
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    gap={24}
                    fill="rgba(0,0,0,0.88)"
                    padding={cardPadding}
                    radius={40}
                    scale={0}
                    opacity={0}
                    maxWidth={maxContentWidth}
                    stroke="rgba(0,255,153,0.3)"
                    lineWidth={2}
                    shadowColor="rgba(0,0,0,0.7)"
                    shadowBlur={50}
                    shadowOffset={[0, 15]}
                >
                    <Txt
                        text={el.text || el.title}
                        fill="#00ff99"
                        fontSize={80}
                        fontWeight={800}
                        textWrap={true}
                        width={innerWidth}
                        textAlign="center"
                        lineHeight={96}
                    />
                    {el.subtext && (
                        <Txt
                            text={el.subtext}
                            fill="white"
                            fontSize={46}
                            fontWeight={500}
                            textWrap={true}
                            width={innerWidth}
                            textAlign="center"
                            lineHeight={60}
                        />
                    )}
                </Rect>
            );
        } else if (el.type === 'FigureShow') {
            const cardPadding = 50;
            const innerWidth = Math.min(1000, maxContentWidth - cardPadding * 2);
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    gap={24}
                    fill="rgba(0,0,0,0.85)"
                    padding={cardPadding}
                    radius={40}
                    opacity={0}
                    y={100}
                    maxWidth={maxContentWidth}
                    stroke="rgba(0,210,255,0.3)"
                    lineWidth={2}
                    shadowColor="rgba(0,0,0,0.6)"
                    shadowBlur={40}
                    shadowOffset={[0, 15]}
                >
                    {el.image_url && (
                        <Rect layout radius={175} clip={true} width={350} height={350}>
                            <Img src={getAbs(el.image_url)} width="100%" height="100%" />
                        </Rect>
                    )}
                    <Txt
                        text={el.name}
                        fill="#00d2ff"
                        fontSize={64}
                        fontWeight={800}
                        textWrap={true}
                        width={innerWidth}
                        textAlign="center"
                        lineHeight={78}
                    />
                </Rect>
            );
        } else if (el.type === 'FigureQuote') {
            const cardPadding = 50;
            const imageSize = 300;
            const textSectionWidth = maxContentWidth - imageSize - cardPadding * 2 - 40;
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="row"
                    alignItems="center"
                    gap={40}
                    fill="rgba(0,0,0,0.88)"
                    padding={cardPadding}
                    radius={40}
                    opacity={0}
                    maxWidth={maxContentWidth}
                    stroke="rgba(255,140,0,0.35)"
                    lineWidth={2}
                    shadowColor="rgba(0,0,0,0.7)"
                    shadowBlur={50}
                    shadowOffset={[0, 15]}
                >
                    {el.image_url && (
                        <Rect layout radius={imageSize / 2} clip={true} width={imageSize} height={imageSize}>
                            <Img src={getAbs(el.image_url)} width="100%" height="100%" />
                        </Rect>
                    )}
                    <Layout layout direction="column" gap={20} width={textSectionWidth}>
                        <Txt
                            text={`"${el.quote}"`}
                            fill="white"
                            fontSize={44}
                            fontStyle="italic"
                            textWrap={true}
                            width={textSectionWidth}
                            lineHeight={58}
                        />
                        <Txt
                            text={`— ${el.name}`}
                            fill="#ff8c00"
                            fontSize={38}
                            fontWeight={800}
                            textWrap={true}
                            width={textSectionWidth}
                            lineHeight={50}
                        />
                    </Layout>
                </Rect>
            );
        } else if (el.type === 'ObjectShow') {
            const cardPadding = 50;
            const innerWidth = Math.min(1100, maxContentWidth - cardPadding * 2);
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    gap={24}
                    fill="rgba(15,23,42,0.92)"
                    padding={cardPadding}
                    radius={40}
                    opacity={0}
                    maxWidth={maxContentWidth}
                    stroke="rgba(255,255,255,0.2)"
                    lineWidth={2}
                    shadowColor="rgba(0,0,0,0.6)"
                    shadowBlur={50}
                    shadowOffset={[0, 15]}
                >
                    {el.image_url && (
                        <Rect layout radius={24} clip={true} width={680} height={400}>
                            <Img src={getAbs(el.image_url)} width="100%" height="100%" />
                        </Rect>
                    )}
                    <Txt
                        text={el.object_name}
                        fill="white"
                        fontSize={64}
                        fontWeight={800}
                        textWrap={true}
                        width={innerWidth}
                        textAlign="center"
                        lineHeight={78}
                    />
                </Rect>
            );
        } else if (el.type === 'NewsClipping') {
            const cardPadding = 50;
            const innerWidth = maxContentWidth - cardPadding * 2;
            const headlineText = el.headline || el.text || '';
            const headlineFontSize = headlineText.length > 120 ? 44 : (headlineText.length > 80 ? 50 : 56);
            const headlineLineHeight = Math.round(headlineFontSize * 1.35);

            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    gap={24}
                    fill="#f8fafc"
                    padding={cardPadding}
                    radius={32}
                    shadowColor="rgba(0,0,0,0.6)"
                    shadowBlur={60}
                    shadowOffset={[0, 20]}
                    stroke="#e2e8f0"
                    lineWidth={3}
                    opacity={0}
                    width={maxContentWidth}
                >
                    <Layout layout direction="row" justifyContent="space-between" alignItems="center" width="100%">
                        <Txt text={el.source || 'MARKET REPORT'} fill="#0f172a" fontSize={38} fontWeight={900} />
                        <Txt text={el.date || ''} fill="#64748b" fontSize={34} fontWeight={600} />
                    </Layout>
                    <Rect layout width="100%" height={4} fill="#0f172a" />
                    <Txt
                        text={headlineText}
                        fill="#0f172a"
                        fontSize={headlineFontSize}
                        fontWeight={800}
                        lineHeight={headlineLineHeight}
                        textWrap={true}
                        width={innerWidth}
                    />
                    {el.image_url && (
                        <Rect layout radius={16} clip={true} width="100%" height={380}>
                            <Img src={getAbs(el.image_url)} width="100%" height="100%" />
                        </Rect>
                    )}
                </Rect>
            );
        } else if (el.type === 'MetricCard') {
            const cardPadding = 50;
            const innerWidth = Math.min(1100, maxContentWidth - cardPadding * 2);
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    gap={20}
                    fill="rgba(15, 23, 42, 0.94)"
                    stroke="rgba(0, 210, 255, 0.4)"
                    lineWidth={3}
                    padding={cardPadding}
                    radius={40}
                    scale={0}
                    opacity={0}
                    maxWidth={maxContentWidth}
                    shadowColor="rgba(0,0,0,0.7)"
                    shadowBlur={50}
                    shadowOffset={[0, 15]}
                >
                    <Txt
                        text={el.metric_name ? el.metric_name.toUpperCase() : 'METRIC'}
                        fill="#94a3b8"
                        fontSize={44}
                        fontWeight={700}
                        textWrap={true}
                        width={innerWidth}
                        textAlign="center"
                        lineHeight={54}
                    />
                    <Txt
                        text={el.metric_value}
                        fill="#00d2ff"
                        fontSize={110}
                        fontWeight={900}
                        textWrap={true}
                        width={innerWidth}
                        textAlign="center"
                        lineHeight={130}
                    />
                </Rect>
            );
        } else if (el.type === 'BulletList') {
            const cardPadding = 50;
            const innerWidth = maxContentWidth - cardPadding * 2;
            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    gap={20}
                    fill="rgba(15, 23, 42, 0.92)"
                    padding={cardPadding}
                    radius={40}
                    opacity={0}
                    y={100}
                    width={maxContentWidth}
                    stroke="rgba(0, 255, 153, 0.3)"
                    lineWidth={2}
                    shadowColor="rgba(0,0,0,0.7)"
                    shadowBlur={50}
                    shadowOffset={[0, 15]}
                >
                    <Txt
                        text={el.title || 'Key Takeaways'}
                        fill="#00ff99"
                        fontSize={56}
                        fontWeight={800}
                        textWrap={true}
                        width={innerWidth}
                        lineHeight={68}
                    />
                    <Rect layout width="100%" height={4} fill="#334155" />
                    <Layout layout direction="column" gap={16} width="100%">
                        {el.bullets?.map((b: string) => (
                            <Txt
                                text={`•  ${b}`}
                                fill="#f1f5f9"
                                fontSize={40}
                                fontWeight={500}
                                textWrap={true}
                                width={innerWidth}
                                lineHeight={56}
                            />
                        ))}
                    </Layout>
                </Rect>
            );
        } else if (el.type === 'AnimatedGraph') {
            const cardWidth = Math.min(1360, maxContentWidth);
            const cardHeight = Math.round(cardWidth * 9 / 16);
            const framesPattern = el.graph_frames_pattern || (el.graph_video ? el.graph_video.replace(/\.mp4$/, '_frames/frame_%04d.jpg') : null);
            const initialFrame = framesPattern ? getAbs(framesPattern.replace('%04d', '0001')) : (el.image_url ? getAbs(el.image_url) : '');
            const frameSignal = createSignal(initialFrame);
            graphFrameSignals[index] = frameSignal;

            return (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    gap={16}
                    fill="rgba(15, 23, 42, 0.96)"
                    stroke="rgba(0, 255, 153, 0.4)"
                    lineWidth={4}
                    radius={36}
                    padding={24}
                    shadowColor="rgba(0,0,0,0.85)"
                    shadowBlur={60}
                    shadowOffset={[0, 20]}
                    opacity={0}
                    scale={0.8}
                    maxWidth={maxContentWidth}
                >
                    {el.title && (
                        <Txt
                            text={el.title}
                            fill="#00ff99"
                            fontSize={44}
                            fontWeight={800}
                            textAlign="center"
                            lineHeight={54}
                            textWrap={true}
                            width={cardWidth - 48}
                        />
                    )}
                    <Rect layout radius={20} clip={true} width={cardWidth - 48} height={cardHeight - 48}>
                        <Img
                            src={frameSignal}
                            width="100%"
                            height="100%"
                        />
                    </Rect>
                </Rect>
            );
        }
        return <Rect ref={nodeRef} opacity={0} />;
    }

    view.add(
        <Rect ref={overlayLayer} width="100%" height="100%">
            {elements.map((el, idx) => renderElementNode(el, idx))}
        </Rect>
    );

    let currentFrame = 0;

    for (let idx = 0; idx < elements.length; idx++) {
        const el = elements[idx];
        const ref = elementRefs[idx];

        const start = (el.start_time || 0) * fps;
        let end = (el.end_time || 0) * fps;
        if (end <= start) end = start + fps * 2;
        const durationSec = (end - start) / fps;

        const waitBefore = (start - currentFrame) / fps;
        if (waitBefore > 0) {
            yield* waitFor(waitBefore);
            currentFrame += waitBefore * fps;
        }

        const animInDuration = 0.5;
        const animOutDuration = el.type === 'AnimatedGraph' ? 0.4 : 0.5;
        const displayWait = Math.max(0.5, durationSec - animInDuration - animOutDuration);

        if (el.type === 'AnimatedGraph') {
            const frameSignal = graphFrameSignals[idx];
            const framesPattern = el.graph_frames_pattern || (el.graph_video ? el.graph_video.replace(/\.mp4$/, '_frames/frame_%04d.jpg') : null);
            const totalFrames = el.graph_frames_count || 240;

            console.log(`[MarketNews-Revideo] [Graph] Displaying AnimatedGraph card frame-by-frame at frame ${currentFrame} (t=${(currentFrame / fps).toFixed(2)}s, duration=${durationSec.toFixed(2)}s, totalFrames=${totalFrames})...`);
            yield* tween(durationSec, (value, time) => {
                if (frameSignal && framesPattern) {
                    const frameIndex = Math.min(totalFrames, Math.max(1, Math.floor(time * fps) + 1));
                    const frameNumStr = String(frameIndex).padStart(4, '0');
                    const resolvedPath = getAbs(framesPattern.replace('%04d', frameNumStr));
                    frameSignal(resolvedPath);
                }
                if (time < animInDuration) {
                    const p = easeInOutCubic(time / animInDuration);
                    ref().opacity(p);
                    ref().scale(0.8 + 0.2 * p);
                } else if (time > durationSec - animOutDuration) {
                    const p = easeInOutCubic((durationSec - time) / animOutDuration);
                    ref().opacity(p);
                    ref().scale(0.8 + 0.2 * p);
                } else {
                    ref().opacity(1);
                    ref().scale(1);
                }
            });
            console.log(`[MarketNews-Revideo] [Graph] AnimatedGraph complete at frame ${start + durationSec * fps}`);
        } else if (el.type === 'Title' || el.type === 'MetricCard') {
            yield* all(
                ref().opacity(1, animInDuration * 0.5),
                ref().scale(1, animInDuration, easeInOutCubic)
            );
            yield* waitFor(displayWait);
            yield* all(
                ref().opacity(0, animOutDuration),
                ref().scale(0, animOutDuration, easeInOutCubic)
            );
        } else if (el.type === 'FigureShow' || el.type === 'BulletList') {
            yield* all(
                ref().opacity(1, animInDuration),
                ref().y(0, animInDuration, easeInOutCubic)
            );
            yield* waitFor(displayWait);
            yield* all(
                ref().opacity(0, animOutDuration),
                ref().y(-100, animOutDuration, easeInOutCubic)
            );
        } else {
            // FigureQuote, ObjectShow, NewsClipping
            yield* ref().opacity(1, animInDuration, easeInOutCubic);
            yield* waitFor(displayWait);
            yield* ref().opacity(0, animOutDuration, easeInOutCubic);
        }

        const totalElapsedFrames = durationSec * fps;
        currentFrame = start + totalElapsedFrames;
    }

    const remainingTime = (durationInFrames - currentFrame) / fps;
    if (remainingTime > 0) {
        yield* waitFor(remainingTime);
    }
});

