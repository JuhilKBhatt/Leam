import {makeScene2D, Audio, Txt, Img, Rect, Layout, Line} from '@revideo/2d';
import {createRef, waitFor, useScene, all, tween, easeInOutCubic} from '@revideo/core';
import {createOutroOverlay, outroFrameSrc} from './utils/outro';

export default makeScene2D('StockComparison', function* (view) {
    const variables = useScene().variables;
    
    const company_a = variables.get('company_a', '')();
    const ticker_a = variables.get('ticker_a', '')();
    const company_b = variables.get('company_b', '')();
    const ticker_b = variables.get('ticker_b', '')();
    const years = variables.get('years', 5)();
    const initial_investment = variables.get('initial_investment', 1000)();
    const final_a = variables.get('final_a', 0)();
    const final_b = variables.get('final_b', 0)();
    const logo_a = variables.get('logo_a', '')();
    const logo_b = variables.get('logo_b', '')();
    const voiceover_audio = variables.get('voiceover_audio', '')();
    const bg_music = variables.get('bg_music', '')();
    const prices = variables.get('prices', [] as any[])();
    const durationInFrames = variables.get('durationInFrames', 900)();
    
    const fps = 30;
    const width = 1080;
    const height = 1920;
    const part1EndFrame = variables.get('part1EndFrame', 60)();

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };

    if (bg_music) view.add(<Audio src={getAbs(bg_music)} play={true} volume={0.05} />);
    if (voiceover_audio) view.add(<Audio src={getAbs(voiceover_audio)} play={true} volume={1} />);

    const colorA = "#00d2ff";
    const colorB = "#ff8c00";

    const valueA = (price: number) => (initial_investment / (prices[0]?.price_a || 1)) * price;
    const valueB = (price: number) => (initial_investment / (prices[0]?.price_b || 1)) * price;

    const maxPrice = prices.length ? Math.max(...prices.map((p: any) => Math.max(valueA(p.price_a), valueB(p.price_b)))) : 1;
    const minPrice = prices.length ? Math.min(...prices.map((p: any) => Math.min(valueA(p.price_a), valueB(p.price_b)))) : 0;

    const padding = 100;
    const chartWidth = width - padding * 2;
    const chartHeight = height / 2;

    const getX = (index: number) => -width/2 + padding + (index / Math.max(1, prices.length - 1)) * chartWidth;
    const getY = (val: number) => {
        const range = maxPrice - minPrice;
        return (chartHeight / 2) - ((val - minPrice) / (range || 1)) * chartHeight;
    };

    const phase1Node = createRef<Rect>();
    view.add(
        <Rect ref={phase1Node} width="100%" height="100%" fill="#111" direction="column" alignItems="center" justifyContent="center">
            <Txt text={`What if you invested $${initial_investment} in...`} fill="white" fontSize={60} y={-300} />
            <Layout layout direction="row" gap={80} alignItems="center">
                <Layout layout direction="column" alignItems="center">
                    {logo_a ? <Img src={getAbs(logo_a)} width={300} height={300} radius={30} fill="white" padding={20} />
                            : <Rect width={300} height={300} fill={colorA} radius={30} />}
                    <Txt text={company_a} fill={colorA} fontSize={50} y={40} />
                </Layout>
                <Txt text="VS" fill="#666" fontSize={100} fontWeight={900} />
                <Layout layout direction="column" alignItems="center">
                    {logo_b ? <Img src={getAbs(logo_b)} width={300} height={300} radius={30} fill="white" padding={20} />
                            : <Rect width={300} height={300} fill={colorB} radius={30} />}
                    <Txt text={company_b} fill={colorB} fontSize={50} y={40} />
                </Layout>
            </Layout>
        </Rect>
    );

    const phase2Node = createRef<Rect>();
    const chartLineA = createRef<Line>();
    const chartLineB = createRef<Line>();
    const currentPriceTxtA = createRef<Txt>();
    const currentPriceTxtB = createRef<Txt>();
    const currentDateTxt = createRef<Txt>();
    const summaryNode = createRef<Layout>();

    view.add(
        <Rect ref={phase2Node} width="100%" height="100%" fill="#111" y={height}>
            <Layout layout direction="row" justifyContent="space-between" width={chartWidth} y={-700} x={0}>
                <Layout layout direction="column" alignItems="start">
                    {logo_a && <Img src={getAbs(logo_a)} width={80} height={80} radius={15} fill="white" padding={10} />}
                    <Txt text={ticker_a} fill={colorA} fontSize={60} />
                    <Txt ref={currentPriceTxtA} text="" fill="#0f0" fontSize={50} />
                </Layout>
                <Layout layout direction="column" alignItems="end">
                    {logo_b && <Img src={getAbs(logo_b)} width={80} height={80} radius={15} fill="white" padding={10} />}
                    <Txt text={ticker_b} fill={colorB} fontSize={60} />
                    <Txt ref={currentPriceTxtB} text="" fill="#0f0" fontSize={50} />
                </Layout>
            </Layout>

            <Txt text={`${years} Year Performance`} fill="#aaa" fontSize={40} y={-500} />
            <Txt ref={currentDateTxt} text="" fill="#888" fontSize={30} y={-450} />

            <Line points={[[-width/2 + padding, chartHeight/2], [width/2 - padding, chartHeight/2]]} stroke="#444" lineWidth={2} y={100} />
            <Line points={[[-width/2 + padding, -chartHeight/2], [-width/2 + padding, chartHeight/2]]} stroke="#444" lineWidth={2} y={100} />

            <Line ref={chartLineA} points={prices.map((p: any, i: number) => [getX(i), getY(valueA(p.price_a))])} stroke={colorA} lineWidth={8} end={0} y={100} />
            <Line ref={chartLineB} points={prices.map((p: any, i: number) => [getX(i), getY(valueB(p.price_b))])} stroke={colorB} lineWidth={8} end={0} y={100} />

            <Layout layout ref={summaryNode} direction="column" y={650} alignItems="center" opacity={0}>
                <Txt text={`Initial Investment: $${initial_investment.toFixed(2)}`} fill="white" fontSize={50} />
                <Txt text={`${ticker_a} ${final_a - initial_investment >= 0 ? 'Gain' : 'Loss'}: $${Math.abs(final_a - initial_investment).toFixed(2)}`} fill={final_a >= initial_investment ? '#0f0' : '#f00'} fontSize={50} y={120} />
                <Txt text={`${ticker_b} ${final_b - initial_investment >= 0 ? 'Gain' : 'Loss'}: $${Math.abs(final_b - initial_investment).toFixed(2)}`} fill={final_b >= initial_investment ? '#0f0' : '#f00'} fontSize={50} y={240} />
            </Layout>
        </Rect>
    );

    const outro = createOutroOverlay(getAbs, view);

    // 0 to part1End
    yield* waitFor(part1EndFrame / fps);

    // Transition Phase 1 -> Phase 2
    yield* all(
        phase1Node().y(-height, 1, easeInOutCubic),
        phase2Node().y(0, 1, easeInOutCubic)
    );

    outro.ref().opacity(1);

    const chartDrawTime = (durationInFrames - part1EndFrame - 60) / fps;
    yield* tween(chartDrawTime, value => {
        const progress = easeInOutCubic(value);
        chartLineA().end(progress);
        chartLineB().end(progress);
        
        const idx = Math.min(Math.floor(progress * prices.length), prices.length - 1);
        if (prices[idx]) {
            const p = prices[idx];
            const currA = valueA(p.price_a);
            const currB = valueB(p.price_b);
            currentPriceTxtA().text(`$${currA.toFixed(2)} ${currA >= initial_investment ? '↑' : '↓'}`);
            currentPriceTxtA().fill(currA >= initial_investment ? '#0f0' : '#f00');
            currentPriceTxtB().text(`$${currB.toFixed(2)} ${currB >= initial_investment ? '↑' : '↓'}`);
            currentPriceTxtB().fill(currB >= initial_investment ? '#0f0' : '#f00');
            currentDateTxt().text(p.date);
        }

        // Animate outro frames
        const currentFrame = Math.floor(value * chartDrawTime * fps);
        if (currentFrame >= 1 && currentFrame <= outro.frameCount) {
            outro.src(outroFrameSrc(getAbs, currentFrame));
        }
    });

    yield* summaryNode().opacity(1, 0.5);

    const remainingTime = (durationInFrames - part1EndFrame - chartDrawTime*fps - 30) / fps;
    if (remainingTime > 0) yield* waitFor(remainingTime);
});
