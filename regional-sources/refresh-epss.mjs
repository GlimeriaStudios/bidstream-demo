import { writeFile } from 'node:fs/promises';

const url = 'https://www.epss.gov.et/epss/tenders?status=active';
const response = await fetch(url, { signal: AbortSignal.timeout(30000) });
if (!response.ok) throw new Error('EPSS returned HTTP ' + response.status);
const html = await response.text();
function plain(text) {
  const entities = { amp: '&', quot: '"', apos: "'", nbsp: ' ', lt: '<', gt: '>' };
  return (text || '').replace(/<[^>]*>/g, ' ').replace(/&(amp|quot|apos|nbsp|lt|gt);/g, (_, key) => entities[key])
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n))).replace(/\s+/g, ' ').trim();
}

const notices = [];
for (const card of html.split(/<div\s+class="tender-card"\s*>/i).slice(1)) {
  const link = card.match(/<h3\s+class="tender-title"[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/i);
  const detail = new URL(link?.[1] || '', url);
  const id = detail.pathname.match(/^\/epss\/tenders\/(\d+)$/)?.[1];
  const dateText = plain(card.match(/<div\s+class="deadline-date">([\s\S]*?)<\/div>/i)?.[1]);
  const date = Date.parse(dateText + ' 00:00 UTC');
  if (detail.origin !== new URL(url).origin || !id || !plain(link?.[2]) || !Number.isFinite(date)) {
    throw new Error('EPSS tender card format changed');
  }
  notices.push({
    id: 'et-epss-' + id, title: plain(link[2]), country: 'Ethiopia', buyer: 'Ethiopian Pharmaceutical Supply Service',
    source: 'Ethiopia EPSS', url: detail.href, published: '', deadline: new Date(date).toISOString().slice(0, 10),
    type: plain(card.match(/<span\s+class="tender-type-badge[^"]*">([\s\S]*?)<\/span>/i)?.[1]) || 'Tender notice',
    description: plain(card.match(/<div\s+class="tender-category">([\s\S]*?)<\/div>/i)?.[1]),
  });
}
if (!notices.length && !/no (?:active )?tenders (?:found|available)/i.test(plain(html))) {
  throw new Error('EPSS returned no recognizable tender listing');
}
await writeFile(new URL('./ethiopia-epss.json', import.meta.url), JSON.stringify({
  checkedAt: new Date().toISOString(), notices,
}, null, 2) + '\n');
console.log('EPSS notices:', notices.length);
