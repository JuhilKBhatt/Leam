import { renderVideo } from '@revideo/renderer';
import * as fs from 'fs';
import * as path from 'path';

// Monkey-patch @revideo/ffmpeg's resolvePath so it can correctly find audio/video assets.
// By default, Revideo's resolvePath assumes all assets are relative to `../public`, which fails
// for Vite virtual paths (/@fs/...), workspace-relative paths, and absolute filesystem paths.
try {
    const ffmpegUtils = require('@revideo/ffmpeg/dist/utils');
    const originalResolvePath = ffmpegUtils.resolvePath;
    ffmpegUtils.resolvePath = function (output: string, assetPath: string): string {
        if (!assetPath) return assetPath;

        let cleanPath = assetPath;
        if (cleanPath.startsWith('/@fs/')) {
            cleanPath = cleanPath.slice('/@fs'.length);
        } else if (cleanPath.startsWith('/@fs')) {
            cleanPath = cleanPath.slice('/@fs'.length);
        }

        // Web URLs or data URIs
        if (cleanPath.startsWith('http://') || cleanPath.startsWith('https://') || cleanPath.startsWith('data:')) {
            return cleanPath;
        }

        // 1. Direct absolute path on disk
        if (path.isAbsolute(cleanPath) && fs.existsSync(cleanPath)) {
            return cleanPath;
        }

        // 2. Relative to workspace root (/app or project root)
        const workspaceRoot = path.resolve(__dirname, '..');
        const inWorkspace = path.resolve(workspaceRoot, cleanPath.replace(/^\//, ''));
        if (fs.existsSync(inWorkspace)) {
            return inWorkspace;
        }

        // 3. Relative to current working directory
        const inCwd = path.resolve(process.cwd(), cleanPath);
        if (fs.existsSync(inCwd)) {
            return inCwd;
        }

        // 4. Relative to output directory
        const inOutput = path.resolve(output, cleanPath);
        if (fs.existsSync(inOutput)) {
            return inOutput;
        }

        // 5. Relative to Revideo's default public dir
        const inPublic = path.resolve(output, '../public', cleanPath);
        if (fs.existsSync(inPublic)) {
            return inPublic;
        }

        if (originalResolvePath) {
            return originalResolvePath(output, cleanPath);
        }
        return cleanPath;
    };
    console.log('[Revideo] Successfully patched @revideo/ffmpeg resolvePath for audio support.');
} catch (e) {
    console.warn('[Revideo] Failed to patch @revideo/ffmpeg resolvePath:', e);
}

// Scene-specific resolution map
// Portrait (1080x1920) = YouTube Shorts; Landscape (1920x1080) = standard YouTube
const RESOLUTION_MAP: Record<string, { x: number; y: number }> = {
    StockTimeline:   { x: 1080, y: 1920 },
    RedditStory:     { x: 1080, y: 1920 },
    StockComparison: { x: 1080, y: 1920 },
    MarketNews:      { x: 1920, y: 1080 },
};

async function main() {
    const sceneName = process.argv[2];
    const outputPath = process.argv[3];
    const propsPath = process.argv[4];

    if (!sceneName || !outputPath || !propsPath) {
        console.error("Usage: tsx render.ts <SceneName> <OutputPath> <PropsPath>");
        process.exit(1);
    }

    const props = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
    props._workspaceRoot = path.resolve(__dirname, '..');

    const size = RESOLUTION_MAP[sceneName] || { x: 1080, y: 1920 };
    console.log(`[Revideo] Rendering ${sceneName} at ${size.x}x${size.y} to ${outputPath}...`);
    console.log(`[Revideo] Props to pass as variables:`, props);
    
    // In Revideo, variables can be accessed in the scene. 
    await renderVideo({
        projectFile: path.resolve(__dirname, `./src/${sceneName}Project.ts`),
        variables: props,
        settings: {
            viteConfig: {
                server: {
                    fs: {
                        allow: [props._workspaceRoot]
                    }
                }
            },
            outDir: path.dirname(outputPath),
            outFile: path.basename(outputPath),
            logProgress: true,
            projectSettings: {
                size,
            },
            puppeteer: {
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--enable-gpu-rasterization',
                    '--enable-zero-copy',
                    '--ignore-gpu-blocklist'
                ],
                ...(process.env.PUPPETEER_EXECUTABLE_PATH ? { executablePath: process.env.PUPPETEER_EXECUTABLE_PATH } : {})
            }
        },
    });

    console.log(`[Revideo] Render complete for ${sceneName}.`);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
