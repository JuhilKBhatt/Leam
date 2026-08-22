import { Composition } from 'remotion';
import { RedditStory } from './RedditStory';
import { StockTimeline } from './StockTimeline';

// Load the last generated props so the Studio can preview it automatically!
import defaultStoryProps from '../props_reddit.json';
import defaultStockProps from '../props_stock.json';

export const RemotionVideo: React.FC = () => {
  return (
    <>
      <Composition
        id="RedditStory"
        component={RedditStory}
        durationInFrames={300} // Default, overridden by calculateMetadata
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => {
          return {
            durationInFrames: (props as any).durationInFrames || 300,
          };
        }}
        defaultProps={defaultStoryProps as any}
      />
      
      <Composition
        id="StockTimeline"
        component={StockTimeline}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultStockProps as any}
      />
    </>
  );
};
