const $ = id => document.getElementById(id);
let works = [];
function message(text, error = false) { $('status').textContent = text; $('status').dataset.error = error; }
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Could not save. Try again.');
  return result;
}
function reset() { $('work-form').reset(); $('work-id').value = ''; $('form-heading').textContent = 'Add new work'; $('save').textContent = 'Add to portfolio'; $('cancel').hidden = true; $('preview').replaceChildren(); }
function draw() {
  $('works').replaceChildren(); $('count').textContent = `${works.length} ${works.length === 1 ? 'piece' : 'pieces'}`;
  if (!works.length) { const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'Your next piece starts with a link. Add your first embed on the left.'; $('works').append(p); }
  for (const work of works) {
    const card = document.createElement('article'); card.className = 'work';
    const title = document.createElement('h3'); title.textContent = work.title;
    const meta = document.createElement('p'); meta.textContent = `${work.provider === 'youtube' ? 'YouTube' : 'Instagram'} · ${work.category}`;
    const link = document.createElement('a'); link.href = work.url; link.textContent = work.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    const edit = document.createElement('button'); edit.className = 'secondary'; edit.textContent = 'Edit'; edit.onclick = () => { $('work-id').value = work.id; $('url').value = work.url; $('title').value = work.title; $('category').value = work.category; $('form-heading').textContent = 'Edit work'; $('save').textContent = 'Save changes'; $('cancel').hidden = false; $('preview').replaceChildren(); message('Editing ' + work.title); $('url').focus(); };
    const remove = document.createElement('button'); remove.className = 'delete'; remove.textContent = 'Remove'; remove.onclick = async () => { if (!confirm(`Remove “${work.title}” from your portfolio?`)) return; remove.disabled = true; try { works = await api('/api/works/delete', {id: work.id}); if ($('work-id').value === work.id) reset(); draw(); message('Removed from your portfolio.'); } catch (error) { message(error.message, true); remove.disabled = false; } };
    card.append(title, meta, link, edit, remove); $('works').append(card);
  }
}
$('cancel').onclick = () => { reset(); message(''); };
$('preview-button').onclick = async () => {
  $('preview-button').disabled = true;
  try {
    const work = await api('/api/preview', {url: $('url').value});
    if (!$('work-id').value) $('category').value = work.suggestedCategory;
    const iframe = document.createElement('iframe'); iframe.src = work.embedUrl; iframe.title = 'Work preview'; iframe.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen'; iframe.allowFullscreen = true; iframe.referrerPolicy = 'strict-origin-when-cross-origin'; iframe.style.height = work.provider === 'instagram' ? '560px' : '240px';
    $('preview').replaceChildren(iframe); message('Preview ready. Add a title and save when you’re happy.');
  } catch (error) { message(error.message, true); } finally { $('preview-button').disabled = false; }
};
$('work-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  try { works = await api('/api/works', {id: $('work-id').value || undefined, title: $('title').value, url: $('url').value, category: $('category').value}); reset(); draw(); message('Saved. Your portfolio updates automatically within 15 seconds.'); }
  catch (error) { message(error.message, true); }
  finally { $('save').disabled = false; }
};
api('/api/works').then(items => { works = items; draw(); }).catch(error => message(error.message, true));
