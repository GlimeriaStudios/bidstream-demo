import { writeFile } from 'node:fs/promises';
import { setTimeout as delay } from 'node:timers/promises';

const notices = new Map();
let lastPage = 1;
for (let page = 1; page <= lastPage; page++) {
  const url = new URL('https://tenders.go.ke/api/active-tenders');
  url.search = new URLSearchParams({ perpage: '100', page: String(page) }).toString();
  let response = await fetch(url, { signal: AbortSignal.timeout(30000) });
  if (response.status === 429) {
    const backoff = Number(response.headers.get('retry-after') || 60);
    if (!(backoff >= 0 && backoff <= 120)) throw new Error('PPIP rate limit exceeds refresh window');
    await delay((backoff + 1) * 1000);
    response = await fetch(url, { signal: AbortSignal.timeout(30000) });
  }
  if (!response.ok) throw new Error('PPIP returned HTTP ' + response.status);
  const result = await response.json();
  if (!Array.isArray(result.data) || Number(result.current_page) !== page || !Number.isInteger(result.last_page)) {
    throw new Error('Unexpected PPIP page');
  }
  if (page === 1) lastPage = result.last_page;
  for (const item of result.data) {
    if (!item.id || !item.title) throw new Error('Unrecognized PPIP listing');
    if (item.terminated) continue;
    notices.set(item.id, {
      id: 'ke-ppip-' + item.id, title: item.title, country: 'Kenya', buyer: item.pe?.name || '',
      source: 'Kenya PPIP', url: 'https://tenders.go.ke/tenders/' + encodeURIComponent(item.id),
      published: item.published_at || '', deadline: item.close_at || '',
      type: item.procurement_category?.title || item.procurement_category?.description || 'Tender notice',
      description: [item.tender_ref, item.description].filter(Boolean).join(' · '),
    });
  }
  if (page < lastPage) await delay(1500);
}
await writeFile(new URL('./kenya-ppip.json', import.meta.url), JSON.stringify({
  checkedAt: new Date().toISOString(), notices: [...notices.values()],
}, null, 2) + '\n');
console.log('PPIP notices:', notices.size, 'pages:', lastPage);
