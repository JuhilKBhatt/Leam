import {Rect, Txt, Layout} from '@revideo/2d';
import {
    createRef,
    createSignal,
    Reference,
    SimpleSignal,
    all,
    tween,
    waitFor,
    easeOutBack,
    easeInBack,
    easeOutCubic,
    easeInCubic,
} from '@revideo/core';

export interface DisclaimerOverlay {
    containerRef: Reference<Rect>;
    iconRef: Reference<Rect>;
    contentRef: Reference<Rect>;
    contentWidth: SimpleSignal<number>;
    contentOpacity: SimpleSignal<number>;
    innerX: SimpleSignal<number>;
    fullWidth: number;
    holdDuration: number;
}

export interface DisclaimerOptions {
    /** X position on canvas (default: -840, top-left inside 16:9 safe zone) */
    x?: number;
    /** Y position on canvas (default: -460, top-left inside 16:9 safe zone) */
    y?: number;
    /** Main disclaimer header text */
    title?: string;
    /** Secondary informational text */
    subtext?: string;
    /** How many seconds to hold the expanded message on screen (default: 5.0) */
    holdDuration?: number;
    /** Width of the expanded message capsule (default: 520) */
    fullWidth?: number;
}

/**
 * Creates a "Not Financial Advice" warning disclaimer node and attaches it to the parent view.
 *
 * Visual Choreography:
 * 1. A glowing circular warning badge pops onto the screen with a bounce.
 * 2. An amber/dark glassmorphism capsule slides out smoothly from the right side of the icon.
 * 3. The disclaimer message remains visible for 5.0 seconds.
 * 4. The message capsule slides back into the icon.
 * 5. The circular warning badge retracts and disappears cleanly.
 */
export function createDisclaimerOverlay(
    parent: {add: (node: any) => void},
    options?: DisclaimerOptions,
): DisclaimerOverlay {
    const x = options?.x ?? -840;
    const y = options?.y ?? -460;
    const title = options?.title ?? 'NOT FINANCIAL ADVICE';
    const subtext = options?.subtext ?? 'For informational & educational purposes only';
    const holdDuration = options?.holdDuration ?? 5.0;
    const fullWidth = options?.fullWidth ?? 520;

    const containerRef = createRef<Rect>();
    const iconRef = createRef<Rect>();
    const contentRef = createRef<Rect>();

    const contentWidth = createSignal(0);
    const contentOpacity = createSignal(0);
    const innerX = createSignal(-30);

    parent.add(
        <Rect
            ref={containerRef}
            x={x}
            y={y}
            offset={[-1, 0]}
            layout
            direction="row"
            alignItems="center"
            gap={14}
            zIndex={100}
        >
            {/* Circular Warning Icon */}
            <Rect
                ref={iconRef}
                width={64}
                height={64}
                radius={32}
                fill="#f59e0b"
                stroke="rgba(254, 240, 138, 0.7)"
                lineWidth={3}
                shadowColor="rgba(245, 158, 11, 0.55)"
                shadowBlur={25}
                shadowOffset={[0, 4]}
                alignItems="center"
                justifyContent="center"
                scale={0}
                opacity={0}
            >
                <Txt
                    text="!"
                    fill="#0f172a"
                    fontSize={42}
                    fontWeight={900}
                    textAlign="center"
                    lineHeight={64}
                />
            </Rect>

            {/* Message Capsule (Slides out from behind the icon) */}
            <Rect
                ref={contentRef}
                clip={true}
                width={contentWidth}
                height={64}
                radius={32}
                fill="rgba(15, 23, 42, 0.94)"
                stroke="rgba(245, 158, 11, 0.45)"
                lineWidth={2}
                shadowColor="rgba(0, 0, 0, 0.7)"
                shadowBlur={30}
                shadowOffset={[0, 8]}
                opacity={contentOpacity}
                padding={[0, 24]}
                alignItems="center"
                justifyContent="center"
            >
                <Layout
                    layout
                    direction="column"
                    gap={2}
                    width={fullWidth - 48}
                    x={innerX}
                >
                    <Txt
                        text={title}
                        fill="#f59e0b"
                        fontSize={20}
                        fontWeight={800}
                        letterSpacing={1.2}
                    />
                    <Txt
                        text={subtext}
                        fill="#94a3b8"
                        fontSize={14}
                        fontWeight={500}
                    />
                </Layout>
            </Rect>
        </Rect>
    );

    return {
        containerRef,
        iconRef,
        contentRef,
        contentWidth,
        contentOpacity,
        innerX,
        fullWidth,
        holdDuration,
    };
}

/**
 * Generator that plays the full disclaimer animation:
 * 1. Icon pop-in
 * 2. Message slide-out from icon
 * 3. 5-second hold
 * 4. Message slide-in
 * 5. Icon pop-out
 *
 * Call with `yield* playDisclaimer(overlay);`
 */
export function* playDisclaimer(
    overlay: DisclaimerOverlay,
): Generator<any, void, any> {
    const {
        iconRef,
        contentWidth,
        contentOpacity,
        innerX,
        fullWidth,
        holdDuration,
    } = overlay;

    if (!iconRef()) return;

    // 1. Circular warning icon pops in with a spring bounce
    yield* all(
        iconRef().opacity(1, 0.35, easeOutCubic),
        iconRef().scale(1, 0.4, easeOutBack)
    );

    // 2. Message capsule slides out from the icon
    contentOpacity(1);
    yield* tween(0.65, (value) => {
        const progress = easeOutCubic(value);
        contentWidth(progress * fullWidth);
        innerX((progress - 1) * 40);
    });

    // 3. Hold on screen for 5.0 seconds
    yield* waitFor(holdDuration);

    // 4. Message capsule slides back into the icon
    yield* tween(0.5, (value) => {
        const progress = easeInCubic(value);
        contentWidth((1 - progress) * fullWidth);
        innerX(-progress * 40);
    });
    contentOpacity(0);

    // 5. Circular warning icon pops down and fades away
    yield* all(
        iconRef().opacity(0, 0.3, easeInCubic),
        iconRef().scale(0, 0.35, easeInBack)
    );
}
