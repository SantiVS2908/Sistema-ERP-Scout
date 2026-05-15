import React, { useState, useEffect, useRef, useCallback } from 'react'

// Configuración estática de las ramas tal cual tu código original
const RAMAS_CONFIG = [
  { key: 'manada',       label: 'Manada',                emoji: '🐺', color: '#f4a261', colorBg: '#fff8e1', ages: '6–10 años' },
  { key: 'tropa',        label: 'Tropa Scout',           emoji: '⛺', color: '#2d6a4f', colorBg: '#e8f5e9', ages: '10–14 años' },
  { key: 'comunidad',    label: 'Comunidad',             emoji: '🥾', color: '#457b9d', colorBg: '#e3f2fd', ages: '14–17 años' },
  { key: 'clan',         label: 'Clan Rover',            emoji: '🔥', color: '#9b2226', colorBg: '#fce4ec', ages: '18–21 años' },
  { key: 'jefes',        label: 'Jefes / Scouters',      emoji: '⚜️', color: '#7b4f9e', colorBg: '#f3e5f5', ages: 'Adultos' },
  { key: 'generales',    label: 'Acervo General',        emoji: '📚', color: '#2d6a4f', colorBg: '#d8f3dc', ages: 'Todo el grupo' },
  { key: 'reglamentos',  label: 'Reglamentos Oficiales', emoji: '📋', color: '#555555', colorBg: '#f5f5f5', ages: 'Scouts de México' },
]

const TABS = [
  ...RAMAS_CONFIG.map(r => ({ key: r.key, label: r.label })),
  { key: 'formatos', label: 'Formatos' },
]

/* ── Componente: Portada PDF con PDF.js (Optimizado para Vite) ── */
function PDFCover({ url, colorBg, emoji }) {
  const canvasRef = useRef(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    async function waitForPdfJs(timeout = 8000) {
      const interval = 100
      let elapsed = 0
      while (!window['pdfjsLib'] && elapsed < timeout) {
        await new Promise(r => setTimeout(r, interval))
        elapsed += interval
      }
      return window['pdfjsLib'] || null
    }

    async function render() {
      try {
        const pdfjsLib = await waitForPdfJs()
        if (!pdfjsLib) { 
          setStatus('error') 
          return 
        }
        
        const pdf = await pdfjsLib.getDocument(url).promise
        if (cancelled) return
        
        const page = await pdf.getPage(1)
        if (cancelled) return
        
        const vp = page.getViewport({ scale: 1 })
        const scale = 300 / vp.width
        const scaled = page.getViewport({ scale })
        
        const canvas = canvasRef.current
        if (!canvas) return
        
        canvas.width = scaled.width
        canvas.height = scaled.height
        
        await page.render({ 
          canvasContext: canvas.getContext('2d'), 
          viewport: scaled 
        }).promise
        
        if (!cancelled) setStatus('done')
      } catch (err) {
        if (!cancelled) setStatus('error')
      }
    }
    render()
    return () => { cancelled = true }
  }, [url])

  if (status === 'loading') return <div className="w-full h-full bg-black/5 animate-pulse" />
  if (status === 'error') return (
    <div className="w-full h-full flex items-center justify-center text-4xl relative overflow-hidden" style={{ background: colorBg }}>
      <div className="absolute inset-0 opacity-10 bg-[repeating-linear-gradient(45deg,rgba(255,255,255,0.07)_0px,rgba(255,255,255,0.07)_8px,transparent_8px,transparent_16px)]" />
      <span className="relative z-10">{emoji}</span>
    </div>
  )
  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full object-cover" />
}

/* ── Componente: Modal Visor del PDF ── */
function PDFModal({ doc, emoji, colorBg, onClose }) {
  return (
    <div className="fixed inset-0 z-[500] bg-[#0a1910]/72 backdrop-blur-md flex items-center justify-center p-5" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-[#faf8f4] rounded-[22px] w-full max-w-[720px] max-h-[90vh] flex flex-col shadow-[0_32px_100px_rgba(10,25,16,0.45)] overflow-hidden">
        <div className="p-5 px-6 border-b border-[#1b4332]/12 flex items-start gap-3.5 shrink-0">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0" style={{ background: colorBg }}>{emoji}</div>
          <div className="min-w-0 flex-1">
            <div className="font-serif text-lg font-bold text-[#0f1e14] leading-snug truncate">{doc.nombre}</div>
            <div className="text-xs text-[#2d6a4f] font-mono mt-0.5 truncate">{doc.archivo}</div>
          </div>
          <button className="w-8 h-8 rounded-full bg-[#d8f3dc] hover:bg-[#c5ebd0] border-none cursor-pointer flex items-center justify-center text-[#2d6a4f] shrink-0 transition-colors" onClick={onClose}>✕</button>
        </div>
        <div className="flex-1 min-h-0 h-[440px] bg-[#2a2d2b]">
          <iframe src={doc.url + '#toolbar=1&navpanes=0'} title={doc.nombre} className="w-full h-full border-none block" />
        </div>
        <div className="p-3.5 px-6 border-t border-[#1b4332]/12 flex gap-2.5 items-center shrink-0 flex-wrap">
          <a className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white font-semibold text-xs p-2.5 px-5 rounded-full flex items-center gap-1.5 transition-all no-underline" href={doc.url} download={doc.archivo}>
            ⬇ Descargar PDF
          </a>
          <a className="bg-[#d8f3dc] hover:bg-[#c5ebd0] text-[#2d6a4f] font-semibold text-xs p-2.5 px-5 rounded-full flex items-center gap-1.5 transition-all no-underline" href={doc.url} target="_blank" rel="noopener noreferrer">
            ↗ Nueva pestaña
          </a>
        </div>
      </div>
    </div>
  )
}

/* ── Componente Interno: RamaContent ── */
function RamaContent({ ramaKey, ramaConfig }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [search, setSearch] = useState('')
  const [openDoc, setOpenDoc] = useState(null)

  useEffect(() => {
    if (!ramaKey) return
    let cancelled = false
    setLoading(true)
    setError(false)
    setDocs([])
    
    fetch(`/api/biblioteca/${ramaKey}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { 
        if (!cancelled) { 
          setDocs(data.documentos || []) 
          setLoading(false) 
        } 
      })
      .catch(() => { 
        if (!cancelled) { 
          setError(true) 
          setLoading(false) 
        } 
      })
    return () => { cancelled = true }
  }, [ramaKey])

  const filtered = search.trim()
    ? docs.filter(d => d.nombre.toLowerCase().includes(search.toLowerCase()) || d.archivo.toLowerCase().includes(search.toLowerCase()))
    : docs

  const isFormatos = ramaKey === 'formatos'
  const emoji = isFormatos ? '📑' : ramaConfig?.emoji || '📄'
  const colorBg = isFormatos ? '#d8f3dc' : ramaConfig?.colorBg || '#d8f3dc'
  const color = isFormatos ? '#2d6a4f' : ramaConfig?.color || '#2d6a4f'
  const ages = isFormatos ? 'Grupo Scout 22' : ramaConfig?.ages || ''
  const title = isFormatos ? 'Formatos del Grupo' : ramaConfig?.label || ''

  return (
    <>
      {/* Search Bar de la biblioteca */}
      <div className="bg-white border-b border-[#1b4332]/12 p-3.5 px-[5vw] sticky top-[68px] z-90 shadow-[0_2px_12px_rgba(15,30,20,0.05)]">
        <div className="relative max-w-[520px]">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#74b494] text-sm">🔍</span>
          <input
            className="w-full pl-11 pr-11 py-2.5 bg-[#faf8f4] border border-[#1b4332]/12 rounded-full text-sm font-sans outline-none focus:border-[#40916c] focus:shadow-[0_0_0_3px_rgba(64,145,108,0.1)] transition-all text-[#0f1e14]"
            placeholder={`Buscar en ${title}…`}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && <button className="absolute right-3.5 top-1/2 -translate-y-1/2 bg-none border-none text-xl cursor-pointer text-[#74b494]" onClick={() => setSearch('')}>×</button>}
        </div>
      </div>

      <div className="p-8 px-[5vw] pb-20">
        {/* Cabecera de la sección activa */}
        <div className="flex items-center gap-3 mb-7 pb-5 border-b border-[#1b4332]/12 flex-wrap">
          <div className="w-3 h-3 rounded-full shrink-0" style={{ background: color }} />
          <div className="font-serif text-2xl font-bold text-[#0f1e14]">{title}</div>
          {ages && <div className="inline-flex bg-[#d8f3dc] text-[#2d6a4f] px-3 py-1 rounded-full text-xs font-semibold">{ages}</div>}
          {!loading && <div className="ml-auto text-xs font-semibold bg-[#f5ede4] text-[#2d6a4f] px-3 py-1 rounded-full">{filtered.length} {filtered.length === 1 ? 'documento' : 'documentos'}</div>}
        </div>

        {/* Loading Spinner */}
        {loading && (
          <div className="text-center py-16 text-[#2d6a4f]">
            <div className="inline-flex gap-1.5 justify-center">
              <div className="w-2 h-2 bg-[#40916c] rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-2 h-2 bg-[#40916c] rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-2 h-2 bg-[#40916c] rounded-full animate-bounce" />
            </div>
            <p className="text-sm mt-3 font-medium">Cargando documentos desde el acervo...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-16 text-[#2d6a4f]">
            <div className="text-4xl mb-3">⚠️</div>
            <p className="text-sm">No se pudo conectar con el librero digital.<br />Inténtalo de nuevo en un momento.</p>
          </div>
        )}

        {/* Empty States */}
        {!loading && !error && filtered.length === 0 && docs.length === 0 && (
          <div className="text-center py-16 text-[#2d6a4f]">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-sm">No hay documentos disponibles en esta sección todavía.</p>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && docs.length > 0 && (
          <div className="text-center py-16 text-[#2d6a4f]">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-sm">No encontramos nada que coincida con "<strong>{search}</strong>"</p>
          </div>
        )}

        {/* Grid de Libros Scouts */}
        {!loading && !error && !isFormatos && filtered.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-5">
            {filtered.map(doc => (
              <div key={doc.archivo} className="bg-white rounded-2xl border border-[#1b4332]/12 overflow-hidden cursor-pointer hover:-translate-y-1.5 hover:shadow-[0_12px_36px_rgba(15,30,20,0.13)] transition-all flex flex-col" onClick={() => setOpenDoc(doc)}>
                <div className="h-[140px] relative overflow-hidden flex items-center justify-center shrink-0">
                  <PDFCover url={doc.url} colorBg={colorBg} emoji={emoji} />
                </div>
                <div className="p-3.5 pt-3.5 flex-1 flex flex-col">
                  <div className="font-serif text-sm font-bold text-[#0f1e14] line-clamp-2 leading-snug mb-1">{doc.nombre}</div>
                  <div className="text-[10px] text-[#74b494] font-mono truncate mb-3">{doc.archivo}</div>
                  <button className="w-full p-2 bg-[#d8f3dc] text-[#40916c] border-none rounded-lg text-xs font-semibold font-sans hover:bg-[#1b4332] hover:text-white transition-colors cursor-pointer mt-auto" onClick={e => { e.stopPropagation(); setOpenDoc(doc) }}>
                    Leer / Abrir →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Lista de Formatos (Estructura lineal) */}
        {!loading && !error && isFormatos && filtered.length > 0 && (
          <div className="flex flex-col gap-2.5 max-w-4xl mx-auto">
            {filtered.map(doc => (
              <div key={doc.archivo} className="bg-white rounded-xl border border-[#1b4332]/12 p-4 px-5 flex items-center gap-4 cursor-pointer hover:translate-x-1 hover:shadow-[0_4px_24px_rgba(15,30,20,0.08)] transition-all" onClick={() => setOpenDoc(doc)}>
                <div className="w-11 h-11 rounded-xl bg-[#d8f3dc] flex items-center justify-center text-xl shrink-0">📄</div>
                <div className="min-w-0 flex-1">
                  <div className="font-serif text-base font-bold text-[#0f1e14] truncate">{doc.nombre}</div>
                  <div className="text-xs text-[#74b494] font-mono mt-0.5 truncate">{doc.archivo}</div>
                </div>
                <div className="flex gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                  <button className="p-2 px-4 rounded-full border-none text-xs font-bold bg-[#d8f3dc] text-[#40916c] hover:bg-[#c5ebd0] cursor-pointer" onClick={() => setOpenDoc(doc)}>👁️ Ver</button>
                  <a className="p-2 px-4 rounded-full border-none text-xs font-bold bg-[#f5ede4] text-[#8b5e3c] hover:bg-[#ede0d7] no-underline" href={doc.url} download={doc.archivo}>⬇️ Bajar</a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Visor Modal de PDF */}
      {openDoc && <PDFModal doc={openDoc} emoji={emoji} colorBg={colorBg} onClose={() => setOpenDoc(null)} />}
    </>
  )
}

/* ── COMPONENTE RAÍZ PRINCIPAL ── */
export const Biblioteca = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState('manada')
  const [counts, setCounts] = useState({})

  // Carga paralela de contadores de libros scouts
  useEffect(() => {
    const keys = [...RAMAS_CONFIG.map(r => r.key), 'formatos']
    keys.forEach(key => {
      fetch(`/api/biblioteca/${key}`)
        .then(r => r.ok ? r.json() : { documentos: [] })
        .then(data => setCounts(prev => ({ ...prev, [key]: (data.documentos || []).length })))
        .catch(() => {})
    })
  }, [])

  const handleTabClick = useCallback((key) => {
    setActiveTab(key)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const totalDocs = Object.values(counts).reduce((s, n) => s + n, 0)
  const totalFormatos = counts['formatos'] || 0
  const currentConfig = RAMAS_CONFIG.find(r => r.key === activeTab)

  return (
    <div className="bg-[#faf8f4] text-[#0f1e14] font-sans min-h-screen selection:bg-[#d8f3dc] relative">
      
      {/* INDICADOR DE DEPURACIÓN FLOTANTE */}
      <div className="fixed bottom-5 right-5 bg-[#1b4332] text-white p-2 px-4 rounded-full text-xs font-semibold z-[1000] shadow-md pointer-events-none font-mono">
        Sección: {activeTab}
      </div>

      {/* TOPBAR NAVIGATION */}
      <nav id="nav" className="sticky top-0 z-[100] h-[68px] flex items-center justify-between px-[5vw] bg-[#faf8f4]/97 backdrop-blur-md shadow-[0_1px_0_rgba(27,67,50,0.12),0_4px_24px_rgba(15,30,20,0.06)]">
        <div className="flex items-center gap-2.5">
          <div className="h-11 flex items-center shrink-0">
            <img src="/static/images/grupo/logo_grupo.jpg" alt="Logo" className="h-11 rounded-md" onError={e => e.currentTarget.style.display='none'} />
          </div>
          <div className="font-serif text-lg font-bold text-[#1b4332] leading-tight">
            Biblioteca Scout
            <span className="block font-sans text-[11px] font-normal text-[#2d6a4f]/75">Grupo 22 Quetzalcóatl · Aguascalientes</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-[#2d6a4f]/70 font-medium">
            <button onClick={() => onNavigate('landing')} className="text-[#2d6a4f] bg-transparent border-none p-0 cursor-pointer font-medium hover:underline">Inicio</button>
            <span className="opacity-40">›</span>
            <strong className="text-[#1b4332] font-semibold">Biblioteca</strong>
          </span>
          <button onClick={() => onNavigate('landing')} className="flex items-center gap-1.5 text-xs font-bold text-[#2d6a4f] bg-[#d8f3dc] hover:bg-[#c5ebd0] p-2 px-4 rounded-full border-none cursor-pointer transition-colors font-sans">
            ← Volver al Inicio
          </button>
        </div>
      </nav>

      {/* HERO HEADER */}
      <div className="bg-[#1b4332] p-12 px-[5vw] pt-14 pb-0 relative overflow-hidden text-white">
        <div className="absolute inset-0 opacity-[0.04] pointer-events-none bg-[repeating-linear-gradient(45deg,rgba(255,255,255,0.07)_0px,rgba(255,255,255,0.07)_8px,transparent_8px,transparent_16px)]" />
        <div className="inline-flex items-center gap-2 bg-white/10 text-[#74b494] px-3.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-[#74b494]/22 mb-4">
          📖 Recursos educativos
        </div>
        <h1 className="font-serif text-3xl md:text-5xl font-black leading-none mb-3">Acervo Scout &amp; <em className="text-[#74b494] not-italic">Formatos</em></h1>
        <p className="text-sm text-white/60 max-w-lg leading-relaxed">Literatura scout organizada por rama y formatos del grupo. Visualiza en línea o descarga cuando lo necesites.</p>
        
        <div className="flex gap-9 mt-7 flex-wrap">
          <div>
            <div className="font-serif text-3xl font-bold leading-none">{totalDocs}</div>
            <div className="text-[11px] text-white/40 uppercase tracking-wide font-medium mt-1">Documentos</div>
          </div>
          <div>
            <div className="font-serif text-3xl font-bold leading-none">{RAMAS_CONFIG.length}</div>
            <div className="text-[11px] text-white/40 uppercase tracking-wide font-medium mt-1">Ramas</div>
          </div>
          <div>
            <div className="font-serif text-3xl font-bold leading-none">{totalFormatos}</div>
            <div className="text-[11px] text-white/40 uppercase tracking-wide font-medium mt-1">Formatos</div>
          </div>
        </div>

        {/* TABS DE FILTRADO REESCRITOS */}
        <div className="flex gap-0 mt-8 border-b border-white/10 overflow-x-auto scrollbar-none snap-x">
          {TABS.map(t => (
            <button
              key={t.key}
              type="button"
              onClick={() => handleTabClick(t.key)}
              className={`p-3 px-4.5 text-xs font-semibold cursor-pointer border-none bg-transparent transition-all border-b-2 snap-start shrink-0 font-sans ${activeTab === t.key ? 'text-white border-b-[#74b494]' : 'text-white/40 border-b-transparent hover:text-white/80 active:scale-98'}`}
            >
              {t.key === 'formatos' ? '📑 ' : ''}{t.label}
              {counts[t.key] > 0 && <span className="ml-1.5 text-[10px] font-normal opacity-60">({counts[t.key]})</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Contenido Dinámico de la Rama Activa */}
      <RamaContent key={activeTab} ramaKey={activeTab} ramaConfig={currentConfig} />
    </div>
  )
}