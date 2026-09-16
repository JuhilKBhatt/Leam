import {makeScene2D, Video, Audio, Txt, Img, Rect, Layout} from '@revideo/2d';
import {createRef, waitFor, useScene, all, tween, easeInOutCubic, spawn} from '@revideo/core';
import {loadLexendFont} from './utils/font';

export default makeScene2D('MarketNews', function* (view) {
    const variables = useScene().variables;
    
    const background_videos = variables.get('background_videos', [] as string[])();
    const info_layer = variables.get('info_layer', [] as any[])();
    const voiceover_audio = variables.get('voiceover_audio', '')();
    const durationInFrames = variables.get('durationInFrames', 900)();
    const fps = 30;
    const width = 1920;
    const height = 1080;
    const frameMargin = 120; // Safe margin from video frame edges
    const maxContentWidth = width - frameMargin * 2; // 1680px safe area

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };

    // Load Lexend font and set as scene default
    yield loadLexendFont(getAbs);
    view.fontFamily('Lexend');

    if (voiceover_audio) view.add(<Audio src={getAbs(voiceover_audio)} play={true} volume={1} />);

    const bgDuration = background_videos.length > 0 ? durationInFrames / background_videos.length : durationInFrames;

    // Backgrounds (we can just add them and use opacity to switch, or sequence them)
    // For simplicity, we just add the first one, or sequence them
    const bgNode = createRef<Video>();
    if (background_videos.length > 0) {
        view.add(<Video ref={bgNode} src={getAbs(background_videos[0])} play={false} volume={0} size={['100%', '100%']} />);
        // Wait a frame for the video to load before starting playback
        yield* waitFor(0);
        bgNode().play();
    } else {
        view.add(<Rect width="100%" height="100%" fill="#111" />);
    }

    // Sequence backgrounds in background task or just linear
    // Actually, generators run sequentially. We can spawn a separate task for backgrounds
    // Revideo provides `spawn` or we can just ignore bg switching for now and use one bg, 
    // or calculate timing. To keep it simple, we just use the first video and loop it,
    // or if we need all, we can change the `src` of the video node at specific times.

    const overlayLayer = createRef<Rect>();
    view.add(<Rect ref={overlayLayer} width="100%" height="100%" />);

    let currentFrame = 0;

    for (const el of info_layer) {
        const start = (el.start_time || 0) * fps;
        let end = (el.end_time || 0) * fps;
        if (end <= start) end = start + fps;
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
                <Rect ref={nodeRef} fill="rgba(0,0,0,0.8)" padding={cardPadding} radius={60} direction="column" alignItems="center" scale={0} maxWidth={maxContentWidth}>
                    <Txt text={el.text} fill="#00ff99" fontSize={90} fontWeight={800} textWrap={true} width={innerWidth} textAlign="center" />
                    {el.subtext && <Txt text={el.subtext} fill="white" fontSize={50} textWrap={true} width={innerWidth} textAlign="center" marginTop={30} />}
                </Rect>
            );
        } else if (el.type === 'FigureShow') {
            const cardPadding = 60;
            const innerWidth = Math.min(1000, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(0,0,0,0.7)" padding={cardPadding} radius={50} opacity={0} y={100} maxWidth={maxContentWidth}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={400} height={400} radius={200} />}
                    <Txt text={el.name} fill="#00d2ff" fontSize={70} textWrap={true} width={innerWidth} textAlign="center" marginTop={30} />
                </Rect>
            );
        } else if (el.type === 'FigureQuote') {
            const cardPadding = 60;
            const textSectionWidth = maxContentWidth - 450 - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} direction="row" alignItems="center" fill="rgba(0,0,0,0.85)" padding={cardPadding} radius={50} opacity={0} maxWidth={maxContentWidth}>
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
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(255,255,255,0.1)" padding={cardPadding} radius={50} opacity={0} maxWidth={maxContentWidth}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={700} height={420} radius={30} />}
                    <Txt text={el.object_name} fill="white" fontSize={70} textWrap={true} width={innerWidth} textAlign="center" marginTop={25} shadowColor="rgba(0,0,0,0.5)" shadowBlur={20} shadowOffset={[0, 10]} />
                </Rect>
            );
        } else if (el.type === 'NewsClipping') {
            const cardPadding = 60;
            const innerWidth = maxContentWidth - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} direction="column" fill="white" padding={cardPadding} radius={30} shadowColor="rgba(0,0,0,0.5)" shadowBlur={60} shadowOffset={[0, 20]} opacity={0} width={maxContentWidth}>
                    <Layout layout direction="row" justifyContent="space-between" width="100%">
                        <Txt text={el.source} fill="black" fontSize={45} fontWeight={900} />
                        <Txt text={el.date} fill="black" fontSize={40} />
                    </Layout>
                    <Rect width="100%" height={4} fill="black" margin={[20, 0]} />
                    <Txt text={el.headline} fill="black" fontSize={60} lineHeight={1.2} textWrap={true} width={innerWidth} />
                    {el.image_url && <Img src={getAbs(el.image_url)} width="100%" height={400} marginTop={30} />}
                </Rect>
            );
        } else if (el.type === 'MetricCard') {
            const cardPadding = 60;
            const innerWidth = Math.min(1000, maxContentWidth - cardPadding * 2);
            node = (
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(255,255,255,0.9)" padding={cardPadding} radius={40} scale={0} maxWidth={maxContentWidth}>
                    <Txt text={el.metric_name ? el.metric_name.toUpperCase() : ''} fill="#555" fontSize={50} textWrap={true} width={innerWidth} textAlign="center" />
                    <Txt text={el.metric_value} fill="#00d2ff" fontSize={120} fontWeight={900} textWrap={true} width={innerWidth} textAlign="center" marginTop={20} />
                </Rect>
            );
        } else if (el.type === 'BulletList') {
            const cardPadding = 60;
            const innerWidth = maxContentWidth - cardPadding * 2;
            node = (
                <Rect ref={nodeRef} direction="column" fill="rgba(0,0,0,0.85)" padding={cardPadding} radius={50} opacity={0} y={100} width={maxContentWidth}>
                    <Txt text={el.title} fill="#00ff99" fontSize={60} textWrap={true} width={innerWidth} />
                    <Rect width="100%" height={4} fill="#333" margin={[20, 0]} />
                    <Layout layout direction="column" gap={20} width="100%">
                        {el.bullets?.map((b: string) => (
                            <Txt text={`•  ${b}`} fill="white" fontSize={42} textWrap={true} width={innerWidth} />
                        ))}
                    </Layout>
                </Rect>
            );
        }

        if (node) {
            overlayLayer().add(node);
            
            // Animate In
            if (el.type === 'Title' || el.type === 'MetricCard') {
                yield* (nodeRef() as any).scale(1, 0.5, easeInOutCubic);
            } else {
                yield* all(
                    (nodeRef() as any).opacity(1, 0.5),
                    (nodeRef() as any).y(0, 0.5, easeInOutCubic)
                );
            }

            // Wait
            yield* waitFor(durationSec - 1);
            
            // Animate Out
            if (el.type === 'Title' || el.type === 'MetricCard') {
                yield* (nodeRef() as any).scale(0, 0.5, easeInOutCubic);
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
