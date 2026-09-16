import {Img, Rect} from '@revideo/2d';
import {createRef, createSignal, Reference, SimpleSignal} from '@revideo/core';

const OUTRO_FRAME_COUNT = 230;
const OUTRO_TEMPLATE_PATH = 'media/video/template/like_subscribe_alpha';

export interface OutroOverlay {
    /** Reference to the Img node (to toggle opacity). */
    ref: Reference<Img>;
    /** Signal controlling the current frame src. */
    src: SimpleSignal<string>;
    /** Total number of frames in the sequence. */
    frameCount: number;
}

/**
 * Creates an outro overlay node and returns handles for controlling it.
 *
 * The overlay preserves the native 16:9 aspect ratio of the frame images
 * regardless of the scene resolution, preventing the squished look that
 * occurs when stretching a landscape image into a portrait canvas.
 *
 * @param getAbs  Helper that resolves a workspace-relative path to a Vite-servable URL.
 * @param parent  The node to attach the overlay to (typically `view`).
 */
export function createOutroOverlay(
    getAbs: (p: string) => string,
    parent: {add: (node: any) => void},
): OutroOverlay {
    const ref = createRef<Img>();
    const src = createSignal(getAbs(`${OUTRO_TEMPLATE_PATH}/frame_001.png`));

    // Native frame size is 3840×2160 (16:9).
    // We centre it and let it scale to fit the shorter axis so it never distorts.
    parent.add(
        <Rect width="100%" height="100%" clip>
            <Img
                ref={ref}
                src={src}
                width={3840}
                height={2160}
                opacity={0}
            />
        </Rect>
    );

    return {ref, src, frameCount: OUTRO_FRAME_COUNT};
}

/**
 * Returns the src path for a given 1-indexed frame number.
 */
export function outroFrameSrc(getAbs: (p: string) => string, frame: number): string {
    const clamped = Math.max(1, Math.min(frame, OUTRO_FRAME_COUNT));
    return getAbs(`${OUTRO_TEMPLATE_PATH}/frame_${clamped.toString().padStart(3, '0')}.png`);
}

/**
 * Generator that plays through the outro frame sequence at 30 fps.
 * Call with `yield* playOutro(...)`.
 */
export function* playOutro(
    overlay: OutroOverlay,
    getAbs: (p: string) => string,
): Generator<void, void, void> {
    if (!overlay.ref()) return;
    overlay.ref().opacity(1);
    for (let i = 1; i <= overlay.frameCount; i++) {
        overlay.src(outroFrameSrc(getAbs, i));
        yield;
    }
}
