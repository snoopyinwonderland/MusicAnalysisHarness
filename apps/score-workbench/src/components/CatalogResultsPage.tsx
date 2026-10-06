import { ArrowLeft, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';

type CatalogItem = { workId: string; title: string; composer: string; source: string; partName: string };
const PAGE_SIZE = 24;

export function CatalogResultsPage() {
  const params = new URLSearchParams(location.search);
  const initialQuery = params.get('q') || '';
  const [input, setInput] = useState(initialQuery), [query, setQuery] = useState(initialQuery);
  const [page, setPage] = useState(Math.max(1, Number(params.get('page')) || 1));
  const [items, setItems] = useState<CatalogItem[]>([]), [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    if (query.trim().length < 2) { setItems([]); setHasMore(false); return }
    const controller = new AbortController(), offset = (page - 1) * PAGE_SIZE;
    setLoading(true); setError('');
    fetch(`/api/catalog/search?q=${encodeURIComponent(query)}&limit=${PAGE_SIZE}&offset=${offset}`, { signal: controller.signal })
      .then(async response => { const data = await response.json(); if (!response.ok) throw new Error(data.error || '검색에 실패했습니다.'); return data })
      .then(data => { setItems(data.items || []); setHasMore(Boolean(data.hasMore)) })
      .catch(reason => { if (reason?.name !== 'AbortError') setError(reason instanceof Error ? reason.message : '검색에 실패했습니다.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) });
    history.replaceState(null, '', `/catalog?q=${encodeURIComponent(query)}&page=${page}`);
    return () => controller.abort();
  }, [query, page]);
  const submit = (event: FormEvent) => { event.preventDefault(); const next = input.trim(); if (next.length >= 2) { setPage(1); setQuery(next) } };
  return <div className='catalog-page'><header className='catalog-page-header'><a href='/' className='catalog-back'><ArrowLeft/> 선율 검색으로 돌아가기</a><span className='brand'><span className='brand-mark'>M</span><span>MUSICANOTE<small>Catalog Search</small></span></span></header><main><p className='kicker'>MUSIC CATALOG</p><h1>키워드 검색</h1><form onSubmit={submit}><Search/><input value={input} onChange={event => setInput(event.target.value)} aria-label='곡명·작곡가·키워드 검색' autoFocus/><button>검색</button></form><div className='catalog-page-summary'><b>“{query}”</b><span>{loading ? '검색 중…' : items.length ? `${(page - 1) * PAGE_SIZE + 1}–${(page - 1) * PAGE_SIZE + items.length}번째 결과` : '검색 결과 없음'}</span></div>{error && <p className='search-error'>{error}</p>}{!loading && <div className='catalog-page-results'>{items.map(item => <a key={item.workId} href={`/score?workId=${encodeURIComponent(item.workId)}&browse=1`}><div><b>{item.title}</b><span>{[item.composer, item.partName].filter(Boolean).join(' · ') || '작곡가 정보 없음'}</span></div><small>{item.source}</small></a>)}</div>}<nav className='catalog-pagination' aria-label='검색 결과 페이지'><button disabled={page===1||loading} onClick={() => setPage(value => value - 1)}><ChevronLeft/> 이전</button><span>{page} 페이지</span><button disabled={!hasMore||loading} onClick={() => setPage(value => value + 1)}>다음 <ChevronRight/></button></nav></main></div>
}
