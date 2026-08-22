import { Composition } from 'remotion';
import { RedditStory } from './RedditStory';

// Load the last generated props so the Studio can preview it automatically!
import defaultStoryProps from '../props_reddit.json';

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
    </>
  );
};
