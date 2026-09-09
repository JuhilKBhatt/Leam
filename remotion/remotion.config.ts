import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPublicDir('../');

Config.setChromiumOpenGlRenderer('angle');
Config.setChromiumDisableWebSecurity(true);
Config.setChromiumCommandLineArgs([
  '--ignore-gpu-blocklist',
  '--enable-gpu-rasterization',
  '--disable-software-rasterizer',
  '--enable-zero-copy'
]);
