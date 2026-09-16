import { makeScene2D, Video, Audio, Txt, Img, Rect, Layout, Line } from '@revideo/2d';
import { createRef, waitFor, useScene, all, tween, map, easeInOutCubic } from '@revideo/core';
import { createOutroOverlay, outroFrameSrc } from './utils/outro';
import { loadLexendFont } from './utils/font';

export default makeScene2D('StockTimeline', function* (view) {
    const variables = useScene().variables;

    const company = variables.get('company', '')();
    const ticker = variables.get('ticker', '')();
    const years = variables.get('years', 5)();
    const initial_investment = variables.get('initial_investment', 1000)();
    const gain = variables.get('gain', 0)();
    const initial_product_image = variables.get('initial_product_image', '')();
    const initial_product_images = variables.get('initial_product_images', initial_product_image ? [initial_product_image] : [])();
    const gain_purchase_image = variables.get('gain_purchase_image', '')();
    const gain_purchase_images = variables.get('gain_purchase_images', gain_purchase_image ? [gain_purchase_image] : [])();
    const voiceover_audio = variables.get('voiceover_audio', '')();
    const bg_music = variables.get('bg_music', '')();
    const prices = variables.get('prices', [] as any[])();
    const durationInFrames = variables.get('durationInFrames', 900)();

    const fps = 30;
    const width = 1080;
    const height = 1920;
    const textMargin = 100; // Safe margin from video frame edges
    const textWidth = width - textMargin * 2; // 880px safe text area
    const part1EndFrame = variables.get('part1EndFrame', 45)();
    const part2EndFrame = variables.get('part2EndFrame', Math.floor(durationInFrames * 2 / 3))();

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };

    // Load Lexend font and set as scene default
    yield loadLexendFont(getAbs);
    view.fontFamily('Lexend');

    // Audio
    if (bg_music) view.add(<Audio src={getAbs(bg_music)} play={true} volume={0.05} />);
    if (voiceover_audio) view.add(<Audio src={getAbs(voiceover_audio)} play={true} volume={1} />);

    // --- Phase 1 ---
    const phase1Node = createRef<Rect>();
    view.add(
        <Rect ref={phase1Node} width="100%" height="100%" fill="#111" opacity={1}>
            <Layout layout direction="column" width="100%" height="100%">
                {initial_product_images.map((img: string) => (
                    <Img src={getAbs(img)} width="100%" grow={1} />
                ))}
            </Layout>
            <Rect width="100%" height="100%" fill="rgba(0,0,0,0.5)" />
            <Txt
                text="What if you didn't buy this?"
                fill="white"
                fontSize={70}
                fontWeight={900}
                y={-100}
                shadowColor="rgba(0,0,0,0.8)"
                shadowBlur={10}
                textWrap={true}
                width={textWidth}
                textAlign="center"
            />
        </Rect>
    );

    // --- Phase 2 ---
    const padding = 100;
    const chartWidth = width - padding * 2;
    const chartHeight = height / 2;

    const maxPrice = prices.length ? Math.max(...prices.map((p: any) => p.price)) : 1;
    const minPrice = prices.length ? Math.min(...prices.map((p: any) => p.price)) : 0;

    const getX = (index: number) => -width / 2 + padding + (index / Math.max(1, prices.length - 1)) * chartWidth;
    const getY = (price: number) => {
        const range = maxPrice - minPrice;
        return (chartHeight / 2) - ((price - minPrice) / (range || 1)) * chartHeight;
    };

    const firstPrice = prices[0]?.price || 0;
    const lastPrice = prices[prices.length - 1]?.price || 0;
    const isUp = lastPrice >= firstPrice;
    const lineColor = isUp ? '#0f0' : '#f00';

    const chart_video = variables.get('chart_video', '')();
    const phase2Node = createRef<Rect>();
    const chartVideoRef = createRef<Video>();
    const chartLine = createRef<Line>();
    const currentPriceTxt = createRef<Txt>();
    const currentValueTxt = createRef<Txt>();
    const currentDateTxt = createRef<Txt>();
    const summaryNode = createRef<Layout>();

    const chartCardSize = 1000;
    const gainPercent = (gain / (initial_investment || 1)) * 100;
    const formatCurrency = (val: number) => Math.abs(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});

    view.add(
        <Rect ref={phase2Node} width="100%" height="100%" fill="#111" opacity={0}>
            {chart_video ? (
                <Rect width={chartCardSize} height={chartCardSize} radius={40} clip y={-120} fill="white" shadowColor="rgba(0,0,0,0.5)" shadowBlur={35}>
                    <Video ref={chartVideoRef} src={getAbs(chart_video)} play={false} size={[chartCardSize, chartCardSize]} />
                </Rect>
            ) : (
                <>
                    <Layout layout direction="column" alignItems="center" y={-650} gap={20} width={textWidth}>
                        <Txt text={`${company} (${ticker})`} fill="white" fontSize={60} textWrap={true} width={textWidth} textAlign="center" />
                        <Txt text={`${years} Year Performance`} fill="#aaa" fontSize={40} textWrap={true} width={textWidth} textAlign="center" />
                        <Txt ref={currentPriceTxt} text="" fill="white" fontSize={50} textWrap={true} width={textWidth} textAlign="center" />
                        <Txt ref={currentValueTxt} text="" fill="white" fontSize={45} textWrap={true} width={textWidth} textAlign="center" />
                        <Txt ref={currentDateTxt} text="" fill="#888" fontSize={30} textWrap={true} width={textWidth} textAlign="center" />
                    </Layout>

                    <Line points={[[-width / 2 + padding, chartHeight / 2], [width / 2 - padding, chartHeight / 2]]} stroke="#444" lineWidth={2} y={100} />
                    <Line points={[[-width / 2 + padding, -chartHeight / 2], [-width / 2 + padding, chartHeight / 2]]} stroke="#444" lineWidth={2} y={100} />

                    <Line
                        ref={chartLine}
                        points={prices.map((p: any, i: number) => [getX(i), getY(p.price)])}
                        stroke={lineColor}
                        lineWidth={8}
                        end={0}
                        y={100}
                    />
                </>
            )}

            <Layout layout ref={summaryNode} direction="column" y={570} alignItems="center" opacity={0} width={textWidth} gap={12}>
                <Txt text={`Initial Investment: $${initial_investment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} fill="white" fontSize={48} textWrap={true} width={textWidth} textAlign="center" />
                <Txt text={`${gain >= 0 ? 'Total Gain' : 'Total Loss'}: ${gain >= 0 ? '▲' : '▼'} $${formatCurrency(gain)}`} fill={gain >= 0 ? '#0f0' : '#f00'} fontSize={58} fontWeight={800} textWrap={true} width={textWidth} textAlign="center" />
                <Txt text={`(${gain >= 0 ? '+' : '-'}${Math.abs(gainPercent).toFixed(2)}%)`} fill={gain >= 0 ? '#0f0' : '#f00'} fontSize={46} fontWeight={700} textWrap={true} width={textWidth} textAlign="center" />
            </Layout>
        </Rect>
    );

    // --- Phase 3 ---
    const phase3Node = createRef<Rect>();
    view.add(
        <Rect ref={phase3Node} width="100%" height="100%" fill="#111" opacity={0}>
            <Layout layout direction="column" width="100%" height="100%">
                {gain_purchase_images.map((img: string) => (
                    <Img src={getAbs(img)} width="100%" grow={1} />
                ))}
            </Layout>
            <Rect width="100%" height="100%" fill="rgba(0,0,0,0.5)" />
            <Txt
                text="You could buy this today!"
                fill="white"
                fontSize={70}
                fontWeight={900}
                y={-100}
                shadowColor="rgba(0,0,0,0.8)"
                shadowBlur={10}
                textWrap={true}
                width={textWidth}
                textAlign="center"
            />
        </Rect>
    );

    // --- Outro ---
    const outro = createOutroOverlay(getAbs, view);

    // Animation Sequence
    // 0 to part1End (approx 1.5s)
    yield* waitFor(part1EndFrame / fps);

    // Fade out phase 1, fade in phase 2
    yield* all(
        phase1Node().opacity(0, 0.5),
        phase2Node().opacity(1, 0.5)
    );

    // Start video playback if using chart video
    if (chart_video && chartVideoRef()) {
        chartVideoRef().play();
    }

    // Show outro overlay
    if (outro.ref()) {
        outro.ref().opacity(1);
    }

    const chartDrawTime = (part2EndFrame - part1EndFrame - 30) / fps;
    yield* tween(chartDrawTime, value => {
        const progress = easeInOutCubic(value);
        if (chartLine()) {
            chartLine().end(progress);
        }

        const idx = Math.min(Math.floor(progress * prices.length), prices.length - 1);
        if (prices[idx]) {
            const p = prices[idx];
            if (currentPriceTxt()) currentPriceTxt().text(`Current Price: $${p.price.toFixed(2)}`);
            const shares = initial_investment / (firstPrice || 1);
            const val = shares * p.price;
            if (currentValueTxt()) currentValueTxt().text(`Investment Value: $${val.toFixed(2)}`);
            if (currentDateTxt()) currentDateTxt().text(p.date);
        }

        // Also update outro sequence
        if (outro.ref()) {
            const currentFrame = Math.floor(value * chartDrawTime * fps);
            if (currentFrame >= 1 && currentFrame <= outro.frameCount) {
                outro.src(outroFrameSrc(getAbs, currentFrame));
            }
        }
    });

    yield* summaryNode().opacity(1, 0.5);

    yield* waitFor(1);

    // Transition to Phase 3
    yield* all(
        phase2Node().opacity(0, 0.5),
        phase3Node().opacity(1, 0.5)
    );

    // Wait until end of duration
    const remainingTime = (durationInFrames - part2EndFrame - 45) / fps;
    if (remainingTime > 0) yield* waitFor(remainingTime);
});
