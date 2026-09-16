import {makeScene2D, Video, Audio, Txt, Img} from '@revideo/2d';
import {createRef, waitFor, useScene, all, tween, easeInOutCubic} from '@revideo/core';
import {createOutroOverlay, playOutro} from './utils/outro';

export default makeScene2D('RedditStory', function* (view) {
    // In Revideo, variables are passed dynamically via renderVideo
    const variables = useScene().variables;
    
    const bgVideoPath = variables.get('bgVideoPath', '')() || variables.get('bg_video', 'media/video/game/14000992_1080_1920_30fps.mp4')();
    const ttsAudioPath = variables.get('ttsAudioPath', '')() || variables.get('tts_audio', '')();
    const musicPath = variables.get('musicPath', '')() || variables.get('bg_music', 'media/audio/music/The_Kitchen_Window.mp3')();
    const words = variables.get('words', [] as any[])();
    const durationInFrames = variables.get('durationInFrames', 300)();
    const fps = 30; // Revideo default is 30

    const projectRoot = variables.get('_workspaceRoot', '')();
    const getAbs = (p: string) => {
        if (p.startsWith('/')) return `/@fs${p}`;
        return `/@fs${projectRoot}/${p}`;
    };
    
    if (bgVideoPath) {
        view.add(
            <Video
                src={getAbs(bgVideoPath)}
                play={true}
                loop={true}
                volume={0}
                size={['100%', '100%']}
            />
        );
    }
    
    if (ttsAudioPath) {
        view.add(<Audio src={getAbs(ttsAudioPath)} play={true} volume={1} />);
    }
    
    if (musicPath) {
        // loop is not native to Audio in Revideo sometimes, but we can set it.
        view.add(<Audio src={getAbs(musicPath)} play={true} volume={0.15} />);
    }
    
    const textRef = createRef<Txt>();
    
    view.add(
        <Txt
            ref={textRef}
            text=""
            fill="#ffffff"
            fontSize={110}
            fontFamily="system-ui, -apple-system, sans-serif"
            fontWeight={900}
            stroke="black"
            lineWidth={4}
            textAlign="center"
            textWrap={true}
            shadowColor="rgba(0,0,0,0.8)"
            shadowBlur={24}
            shadowOffset={[0, 8]}
            width={1080 * 0.85}
            lineHeight={1.2}
            justifyContent="center"
            alignItems="center"
        />
    );
    
    const outro = createOutroOverlay(getAbs, view);

    let currentTime = 0;
    for (const word of words) {
        const waitTime = word.start - currentTime;
        if (waitTime > 0) {
            yield* waitFor(waitTime);
            currentTime += waitTime;
        }
        
        textRef().text(word.word);
        
        const showTime = word.end - word.start;
        if (showTime > 0) {
            yield* waitFor(showTime);
            currentTime += showTime;
        }
        
        textRef().text(""); 
    }
    
    const outroStartSec = (durationInFrames - 210) / fps;
    const timeToOutro = outroStartSec - currentTime;
    
    if (timeToOutro > 0) {
        yield* waitFor(timeToOutro);
    }
    
    yield* playOutro(outro, getAbs);
});
