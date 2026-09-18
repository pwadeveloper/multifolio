import {r as interop} from './rolldown-runtime-S-ySWqyJ.js';
import {i as reactModule, r as jsxModule} from './framework-CXnKph_e.js';
const React = interop(reactModule(), 1);
const {jsx, jsxs} = jsxModule();
const ALLOW = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen';
const youtubeId = url => (/^https:\/\/www\.youtube\.com\/embed\/([A-Za-z0-9_-]{11})$/u.exec(url) || [])[1];
const frame = (src, title) => jsx('iframe', {src, title, loading: 'lazy', allow: ALLOW, allowFullScreen: true, referrerPolicy: 'strict-origin-when-cross-origin'});

/* A cross-origin player cannot be restyled, so a YouTube card shows only the
   thumbnail until it is played. The real player loads on the first click. */
function YouTubeWork({item, videoId}) {
  const [playing, setPlaying] = React.useState(false);
  if (playing) return frame(`${item.embedUrl}?autoplay=1`, item.title);
  return jsxs('button', {type: 'button', className: 'embed-play', onClick: () => setPlaying(true), 'aria-label': `Play ${item.title}`, children: [
    jsx('img', {
      className: 'embed-play-thumb', src: `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`, alt: '', loading: 'lazy', decoding: 'async',
      onError: event => { const image = event.currentTarget; if (!image.dataset.fallback) { image.dataset.fallback = '1'; image.src = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`; } }
    }),
    jsx('span', {className: 'embed-play-icon', 'aria-hidden': 'true'})
  ]});
}

export default function EmbedWorks({filter = 'All'}) {
  const [items, setItems] = React.useState([]);
  React.useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch('/works.json', {cache: 'no-store', signal: controller.signal});
        if (!response.ok) return;
        const data = await response.json();
        if (active && Array.isArray(data)) setItems(data);
      } catch { /* Keep the last successful collection during a connection interruption. */ }
    }
    refresh();
    const timer = setInterval(refresh, 15000);
    window.addEventListener('focus', refresh);
    return () => { active = false; controller.abort(); clearInterval(timer); window.removeEventListener('focus', refresh); };
  }, []);
  const visible = items.filter(item => (filter === 'All' || item.category === filter) && /^https:\/\/(www\.youtube\.com\/embed\/[A-Za-z0-9_-]{11}|www\.instagram\.com\/(p|reel|tv)\/[A-Za-z0-9_-]+\/embed\/)$/u.test(item.embedUrl));
  if (!visible.length) return null;
  return jsx('section', {className: 'embed-works', 'aria-label': 'Video editing work', children: visible.map(item => {
    const videoId = youtubeId(item.embedUrl);
    return jsxs('article', {
      className: `embed-work embed-work--${item.category === 'Reels' ? 'portrait' : 'landscape'} embed-work--${item.provider}`,
      children: [
        videoId ? jsx(YouTubeWork, {item, videoId}) : frame(item.embedUrl, item.title),
        jsxs('div', {className: 'embed-work-caption', children: [jsx('h2', {children: item.title}), jsx('a', {href: item.url, target: '_blank', rel: 'noopener noreferrer', children: 'Open original ↗'})]})
      ]
    }, item.id);
  })});
}
