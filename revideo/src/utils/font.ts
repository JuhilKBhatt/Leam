import '../fonts.css';

let fontLoadedPromise: Promise<void> | null = null;

/**
 * Ensures the Lexend font is loaded and registered in the browser's FontFaceSet
 * before rendering frames, preventing canvas fallback to system/Roboto font.
 */
export function loadLexendFont(getAbs?: (p: string) => string): Promise<void> {
    if (typeof document === 'undefined') return Promise.resolve();

    if (!fontLoadedPromise) {
        fontLoadedPromise = (async () => {
            try {
                // If not already registered in document.fonts, create FontFace explicitly
                if (!document.fonts.check('16px Lexend')) {
                    const fontUrl = getAbs ? getAbs('media/Lexend-Regular.ttf') : '/media/Lexend-Regular.ttf';
                    const font = new FontFace('Lexend', `url(${fontUrl})`);
                    document.fonts.add(font);
                    await font.load();
                }
                await document.fonts.load('16px Lexend');
                await document.fonts.ready;
            } catch (err) {
                console.warn('[Font] Could not load Lexend font via FontFace API, falling back to CSS @font-face:', err);
            }
        })();
    }

    return fontLoadedPromise;
}
