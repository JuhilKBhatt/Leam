import {makeProject} from '@revideo/core';
import MarketNews from './MarketNews?scene';
import RedditStory from './RedditStory?scene';
import StockTimeline from './StockTimeline?scene';
import StockComparison from './StockComparison?scene';

export default makeProject({
    scenes: [MarketNews, RedditStory, StockTimeline, StockComparison],
});
