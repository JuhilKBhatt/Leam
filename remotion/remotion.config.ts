import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPublicDir('../');

Config.setChromiumOpenGlRenderer('vulkan');
Config.setChromiumDisableWebSecurity(true);

Config.overrideFfmpegCommand(({ args }) => {
  // Force NVENC hardware encoding instead of software libx264
  let updatedArgs = [...args];
  const codecIndex = updatedArgs.indexOf('libx264');
  if (codecIndex !== -1) {
    updatedArgs[codecIndex] = 'h264_nvenc';
  }
  
  // Replace software CRF with NVENC's CQ mode
  const crfIndex = updatedArgs.indexOf('-crf');
  if (crfIndex !== -1) {
    updatedArgs[crfIndex] = '-cq';
  }
  
  return updatedArgs;
});
