const fs = require('fs');
const mp4box = require('mp4box');

function parseMp4(filePath) {
    const file = mp4box.createFile();
    file.onReady = (info) => {
        const track = info.videoTracks[0];
        console.log('Video Track:', track.id, track.codec, track.duration, track.timescale, track.nb_samples);
    };
    const b = fs.readFileSync(filePath);
    const ab = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
    ab.fileStart = 0;
    file.appendBuffer(ab);
    file.flush();
}

parseMp4('/Users/J.Bhatt/Desktop/Personal/Projects/Leam/media/video/template/like_subscribe_alpha.webm');
