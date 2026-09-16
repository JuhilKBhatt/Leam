import { defineConfig } from 'vite';
import revideoPlugin from '@revideo/vite-plugin';

export default defineConfig({
  plugins: [revideoPlugin()],
  server: {
    fs: {
      strict: false
    }
  }
});
