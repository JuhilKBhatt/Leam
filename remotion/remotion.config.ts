import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPublicDir('../');

Config.setChromiumOpenGlRenderer('angle');
Config.setChromiumDisableWebSecurity(true);

