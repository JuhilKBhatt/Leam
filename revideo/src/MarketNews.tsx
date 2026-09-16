import {makeScene2D, Video, Audio, Txt, Img, Rect, Layout} from '@revideo/2d';
import {createRef, waitFor, useScene, all, tween, easeInOutCubic, spawn} from '@revideo/core';

export default makeScene2D('MarketNews', function* (view) {
    const variables = useScene().variables;
    
    const background_videos = variables.get('background_videos', [] as string[])();
    const info_layer = variables.get('info_layer', [] as any[])();
    const voiceover_audio = variables.get('voiceover_audio', '')();
    const durationInFrames = variables.get('durationInFrames', 900)();
    const fps = 30;

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };

    if (voiceover_audio) view.add(<Audio src={getAbs(voiceover_audio)} play={true} volume={1} />);

    const bgDuration = background_videos.length > 0 ? durationInFrames / background_videos.length : durationInFrames;

    // Backgrounds (we can just add them and use opacity to switch, or sequence them)
    // For simplicity, we just add the first one, or sequence them
    const bgNode = createRef<Video>();
    if (background_videos.length > 0) {
        view.add(<Video ref={bgNode} src={getAbs(background_videos[0])} play={false} volume={0} size={['100%', '100%']} />);
        // Wait a frame for the video to load before starting playback
        yield* waitFor(0);
        bgNode().play(true);
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
            node = (
                <Rect ref={nodeRef} fill="rgba(0,0,0,0.8)" padding={120} radius={80} direction="column" alignItems="center" scale={0}>
                    <Txt text={el.text} fill="#00ff99" fontSize={160} />
                    {el.subtext && <Txt text={el.subtext} fill="white" fontSize={100} y={120} />}
                </Rect>
            );
        } else if (el.type === 'FigureShow') {
            node = (
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(0,0,0,0.7)" padding={80} radius={60} opacity={0} y={200}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={800} height={800} radius={400} />}
                    <Txt text={el.name} fill="#00d2ff" fontSize={120} y={80} />
                </Rect>
            );
        } else if (el.type === 'FigureQuote') {
            node = (
                <Rect ref={nodeRef} direction="row" alignItems="center" fill="rgba(0,0,0,0.85)" padding={120} radius={80} opacity={0}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={600} height={600} radius={300} marginRight={120} />}
                    <Layout layout direction="column">
                        <Txt text={`"${el.quote}"`} fill="white" fontSize={90} fontStyle="italic" />
                        <Txt text={`- ${el.name}`} fill="#ff8c00" fontSize={70} fontWeight={900} y={80} />
                    </Layout>
                </Rect>
            );
        } else if (el.type === 'ObjectShow') {
            node = (
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(255,255,255,0.1)" padding={100} radius={80} opacity={0}>
                    {el.image_url && <Img src={getAbs(el.image_url)} width={1200} height={800} radius={40} />}
                    <Txt text={el.object_name} fill="white" fontSize={140} y={100} shadowColor="rgba(0,0,0,0.5)" shadowBlur={20} shadowOffset={[0, 10]} />
                </Rect>
            );
        } else if (el.type === 'NewsClipping') {
            node = (
                <Rect ref={nodeRef} direction="column" fill="white" padding={120} radius={40} shadowColor="rgba(0,0,0,0.5)" shadowBlur={100} shadowOffset={[0, 40]} opacity={0}>
                    <Layout layout direction="row" justifyContent="space-between" width="100%">
                        <Txt text={el.source} fill="black" fontSize={70} fontWeight={900} />
                        <Txt text={el.date} fill="black" fontSize={60} />
                    </Layout>
                    <Rect width="100%" height={8} fill="black" y={40} marginBottom={80} />
                    <Txt text={el.headline} fill="black" fontSize={130} lineHeight={1.2} />
                    {el.image_url && <Img src={getAbs(el.image_url)} width="100%" height={800} marginTop={80} />}
                </Rect>
            );
        } else if (el.type === 'MetricCard') {
            node = (
                <Rect ref={nodeRef} direction="column" alignItems="center" fill="rgba(255,255,255,0.9)" padding={100} radius={60} scale={0}>
                    <Txt text={el.metric_name ? el.metric_name.toUpperCase() : ''} fill="#555" fontSize={80} />
                    <Txt text={el.metric_value} fill="#00d2ff" fontSize={200} fontWeight={900} y={40} />
                </Rect>
            );
        } else if (el.type === 'BulletList') {
            node = (
                <Rect ref={nodeRef} direction="column" fill="rgba(0,0,0,0.85)" padding={120} radius={80} opacity={0} y={200}>
                    <Txt text={el.title} fill="#00ff99" fontSize={120} />
                    <Rect width="100%" height={8} fill="#333" y={40} marginBottom={80} />
                    {el.bullets?.map((b: string, i: number) => (
                        <Txt text={`•  ${b}`} fill="white" fontSize={90} y={160 + i * 160} />
                    ))}
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
