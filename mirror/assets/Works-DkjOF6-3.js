import {r as interop} from './rolldown-runtime-S-ySWqyJ.js';
import {i as reactModule, r as jsxModule} from './framework-CXnKph_e.js';
import {t as Nav} from './Nav-BGLgzeL4.js';
import EmbedWorks from './EmbedWorks.js';
const React = interop(reactModule(), 1);
const {jsx, jsxs} = jsxModule();
const filters = [{label:'All',value:'All'},{label:'Reels',value:'Reels',marker:'R'},{label:'Youtube',value:'Youtube',marker:'Y'}];
export default function Works({initialFilter = 'All'}) {
  const [filter, setFilter] = React.useState(filters.some(item => item.value === initialFilter) ? initialFilter : 'All');
  return jsxs('main', {className:'works-page','data-active-filter':filter, children:[
    jsx(Nav, {items:filters,value:filter,onValueChange:setFilter,ariaLabel:'Filter work',fullWidth:true,className:'works-filter-nav'}),
    jsx('h1', {className:'works-intro',children:'Hi, I am Mudia Imasuen (Multimudia), and here is some of my video editing work for short and long form content.'}),
    jsx(EmbedWorks, {filter})
  ]});
}
