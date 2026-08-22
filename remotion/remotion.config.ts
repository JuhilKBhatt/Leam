import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setBrowserExecutable('/usr/bin/chromium');
Config.setPublicDir('../');

Config.setChromiumOptions((options) => {
  return [
    ...options,
    '--ignore-gpu-blocklist',
    '--enable-gpu-rasterization',
    '--enable-zero-copy',
    '--use-gl=egl'
  ];
});
