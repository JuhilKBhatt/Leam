import {makeScene2D, Video, Audio, Txt, Img, Rect, Layout} from '@revideo/2d';
import {createRef, waitFor, useScene, all, tween, easeInOutCubic, spawn} from '@revideo/core';
import {loadLexendFont} from './utils/font';

export default makeScene2D('MarketNews', function* (view) {
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
                    const elEnd = el.end_time !== undefined ? Number(el.end_time) : Number(sc.end_time || elStart + 3);
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

    // Overlay Layer
    const overlayLayer = createRef<Rect>();
    view.add(<Rect ref={overlayLayer} width="100%" height="100%" />);

    let currentFrame = 0;

    for (const el of elements) {
        const start = (el.start_time || 0) * fps;
        let end = (el.end_time || 0) * fps;
        if (end <= start) end = start + fps * 2;
        const durationSec = (end - start) / fps;

        const waitBefore = (start - currentFrame) / fps;
        if (waitBefore > 0) {
            yield* waitFor(waitBefore);
            currentFrame += waitBefore * fps;
        }

        // Draw Element
        let nodeRef = createRef<Rect | Layout>();
        let node: any = null;

        if (el.type === 'Title') {
            const cardPadding = 80;
            const innerWidth = Math.min(1400, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} layout direction="column" alignItems="center" fill="rgba(0,0,0,0.85)" padding={cardPadding} radius={60} scale={0} maxWidth={maxContentWidth}>
                    <Txt text={el.text || el.title} fill="#00ff99" fontSize={90} fontWeight={800} textWrap={true} width={innerWidth} textAlign="center" />
                    {el.subtext && <Txt text={el.subtext} fill="white" fontSize={50} textWrap={true} width={innerWidth} textAlign="center" marginTop={30} />}
                </Rect>
            );
        } else if (el.type === 'FigureShow') {
            const cardPadding = 60;
            const innerWidth = Math.min(1000, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} layout direction="column" alignItems="center" fill="rgba(0,0,0,0.8)" padding={cardPadding} radius={50} opacity={0} y={100} maxWidth={maxContentWidth}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={400} height={400} radius={200} />}
                    <Txt text={el.name} fill="#00d2ff" fontSize={70} textWrap={true} width={innerWidth} textAlign="center" marginTop={30} />
                </Rect>
            );
        } else if (el.type === 'FigureQuote') {
            const cardPadding = 60;
            const textSectionWidth = maxContentWidth - 450 - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} layout direction="row" alignItems="center" fill="rgba(0,0,0,0.85)" padding={cardPadding} radius={50} opacity={0} maxWidth={maxContentWidth}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={350} height={350} radius={175} marginRight={50} />}
                    <Layout layout direction="column" width={textSectionWidth}>
                        <Txt text={`"${el.quote}"`} fill="white" fontSize={48} fontStyle="italic" textWrap={true} width={textSectionWidth} />
                        <Txt text={`- ${el.name}`} fill="#ff8c00" fontSize={40} fontWeight={900} textWrap={true} width={textSectionWidth} marginTop={20} />
                    </Layout>
                </Rect>
            );
        } else if (el.type === 'ObjectShow') {
            const cardPadding = 60;
            const innerWidth = Math.min(1000, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} layout direction="column" alignItems="center" fill="rgba(255,255,255,0.12)" padding={cardPadding} radius={50} opacity={0} maxWidth={maxContentWidth}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={700} height={420} radius={30} />}
                    <Txt text={el.object_name} fill="white" fontSize={70} textWrap={true} width={innerWidth} textAlign="center" marginTop={25} shadowColor="rgba(0,0,0,0.5)" shadowBlur={20} shadowOffset={[0, 10]} />
                </Rect>
            );
        } else if (el.type === 'NewsClipping') {
            const cardPadding = 60;
            const innerWidth = maxContentWidth - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} layout direction="column" fill="white" padding={cardPadding} radius={30} shadowColor="rgba(0,0,0,0.5)" shadowBlur={60} shadowOffset={[0, 20]} opacity={0} width={maxContentWidth}>
                    <Layout layout direction="row" justifyContent="space-between" width="100%">
                        <Txt text={el.source || 'Market Update'} fill="black" fontSize={45} fontWeight={900} />
                        <Txt text={el.date || ''} fill="#555" fontSize={40} />
                    </Layout>
                    <Rect width="100%" height={4} fill="black" margin={[20, 0]} />
                    <Txt text={el.headline || el.text} fill="black" fontSize={60} lineHeight={1.2} textWrap={true} width={innerWidth} />
                    {el.image_url && <Img src={getAbs(el.image_url)} width="100%" height={400} marginTop={30} />}
                </Rect>
            );
        } else if (el.type === 'MetricCard') {
            const cardPadding = 60;
            const innerWidth = Math.min(1100, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} layout direction="column" alignItems="center" fill="rgba(15, 23, 42, 0.92)" stroke="rgba(0, 210, 255, 0.4)" lineWidth={3} padding={cardPadding} radius={40} scale={0} maxWidth={maxContentWidth}>
                    <Txt text={el.metric_name ? el.metric_name.toUpperCase() : ''} fill="#888" fontSize={50} textWrap={true} width={innerWidth} textAlign="center" />
                    <Txt text={el.metric_value} fill="#00d2ff" fontSize={120} fontWeight={900} textWrap={true} width={innerWidth} textAlign="center" marginTop={20} />
                </Rect>
            );
        } else if (el.type === 'BulletList') {
            const cardPadding = 60;
            const innerWidth = maxContentWidth - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} layout direction="column" fill="rgba(0,0,0,0.88)" padding={cardPadding} radius={50} opacity={0} y={100} width={maxContentWidth}>
                    <Txt text={el.title} fill="#00ff99" fontSize={60} textWrap={true} width={innerWidth} />
                    <Rect width="100%" height={4} fill="#333" margin={[20, 0]} />
                    <Layout layout direction="column" gap={20} width="100%">
                        {el.bullets?.map((b: string) => (
                            <Txt text={`•  ${b}`} fill="white" fontSize={42} textWrap={true} width={innerWidth} />
                        ))}
                    </Layout>
                </Rect>
            );
        } else if (el.type === 'AnimatedGraph') {
            const cardWidth = Math.min(1360, maxContentWidth);
            const cardHeight = Math.round(cardWidth * 9 / 16);
            node = (
                <Rect
                    ref={nodeRef}
                    layout
                    direction="column"
                    alignItems="center"
                    fill="rgba(15, 23, 42, 0.95)"
                    stroke="rgba(0, 255, 153, 0.35)"
                    lineWidth={4}
                    radius={36}
                    padding={24}
                    shadowColor="rgba(0,0,0,0.8)"
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
                            fontSize={42}
                            fontWeight={800}
                            textAlign="center"
                            marginBottom={16}
                        />
                    )}
                    {el.graph_video && (
                        <Rect radius={20} clip={true} width={cardWidth - 48} height={cardHeight - 48}>
                            <Video
                                src={getAbs(el.graph_video)}
                                play={true}
                                loop={true}
                                volume={0}
                                size={['100%', '100%']}
                            />
                        </Rect>
                    )}
                </Rect>
            );
        }

        if (node) {
            overlayLayer().add(node);
            yield* waitFor(0);

            // Animate In
            if (el.type === 'Title' || el.type === 'MetricCard') {
                yield* (nodeRef() as any).scale(1, 0.5, easeInOutCubic);
            } else if (el.type === 'AnimatedGraph') {
                yield* all(
                    (nodeRef() as any).opacity(1, 0.5),
                    (nodeRef() as any).scale(1, 0.5, easeInOutCubic)
                );
            } else {
                yield* all(
                    (nodeRef() as any).opacity(1, 0.5),
                    (nodeRef() as any).y(0, 0.5, easeInOutCubic)
                );
            }

            // Wait during display duration
            const displayWait = Math.max(0.2, durationSec - 1.0);
            yield* waitFor(displayWait);

            // Animate Out
            if (el.type === 'Title' || el.type === 'MetricCard') {
                yield* (nodeRef() as any).scale(0, 0.5, easeInOutCubic);
            } else if (el.type === 'AnimatedGraph') {
                yield* all(
                    (nodeRef() as any).opacity(0, 0.4),
                    (nodeRef() as any).scale(0.8, 0.4, easeInOutCubic)
                );
            } else {
                yield* all(
                    (nodeRef() as any).opacity(0, 0.5),
                    (nodeRef() as any).y(-200, 0.5, easeInOutCubic)
                );
            }

            nodeRef().remove();
        }

        currentFrame = end;
    }

    const remainingTime = (durationInFrames - currentFrame) / fps;
    if (remainingTime > 0) {
        yield* waitFor(remainingTime);
    }
});
