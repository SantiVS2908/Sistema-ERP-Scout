import React, { useState, useEffect } from 'react'

// Configuración estática de las secciones
const SECCIONES_CONFIG = {
  manada: {
    emoji: '🐺', title: 'Manada', subtitle: '6 a 10 años',
    color: '#f4a261', bgGradient: 'from-[#fff8e1] to-[#ffe082]',
    marco: 'Inspirada en "El Libro de la Selva" de Rudyard Kipling. Los lobatos viven en la Manada guiada por Akela. Aprenden autoconfianza, amistad y los primeros pasos del método scout a través del juego simbólico.',
    seccionNombre: 'Manada', telefono: '4491042963', jefe: 'Akela',
    msg: 'Hola! Me interesa información sobre la Manada (6-10 años).'
  },
  tropa: {
    emoji: '⛺', title: 'Tropa Scout Omeyocan', subtitle: '10 a 14 años',
    color: '#2d6a4f', bgGradient: 'from-[#e8f5e9] to-[#a5d6a7]',
    marco: 'El corazón del escultismo clásico. Las patrullas de 6–8 scouts aprenden técnicas de campo, orientación, primeros auxilios y liderazgo democrático bajo la guía del Guía Mayor.',
    seccionNombre: 'Tropa', telefono: '4491951715', jefe: 'Scouter Nancy',
    msg: 'Hola! Me interesa información sobre la Tropa Scout (10-14 años).'
  },
  comunidad: {
    emoji: '🥾', title: 'Comunidad', subtitle: '14 a 17 años',
    color: '#457b9d', bgGradient: 'from-[#e3f2fd] to-[#90caf9]',
    marco: 'La etapa del mar y el horizonte. Los scouts desarrollan proyectos propios de servicio social, exploran su identidad y preparan su transición hacia el Clan.',
    seccionNombre: 'Comunidad', telefono: '4492637454', jefe: 'Scouter Montse',
    msg: 'Hola! Me interesa información sobre la Comunidad (14-17 años).'
  },
  clan: {
    emoji: '🔥', title: 'Clan Rover', subtitle: '18 a 21 años',
    color: '#9b2226', bgGradient: 'from-[#fce4ec] to-[#f48fb1]',
    marco: 'La cumbre del método scout. Los rovers son adultos jóvenes comprometidos con el servicio, la aventura y el crecimiento. El clan gestiona sus propios proyectos y rutas de alto impacto.',
    seccionNombre: 'Clan', telefono: '4492312365', jefe: 'Consejero Neto',
    msg: 'Hola! Me interesa información sobre el Clan Rover (18-21 años).'
  },
  jefeGrupo: {
    emoji: '⚜️', title: 'Administración de Grupo', subtitle: 'Administración · Grupo Scout 22',
    color: '#1b4332', bgGradient: 'from-[#1b4332] to-[#2d6a4f]',
    marco: 'La Jefatura coordina todas las secciones del grupo, gestiona el registro y atiende dudas generales sobre inscripciones, actividades y administración.',
    seccionNombre: null, telefono: '4498040164', jefe: 'Chucho',
    msg: 'Hola! Me interesa información general sobre el Grupo Scout 22 Quetzalcoalt.'
  }
}

const MESES_CORTO = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
const DIAS_SEMANA = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']

export const Landing = ({ onNavigate }) => {
  // ---- ESTADOS COMPONENTES ----
  const [scrolled, setScrolled] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [yearsOfHistory, setYearsOfHistory] = useState(20)
  const [heroImages, setHeroImages] = useState(['/static/images/fondos_principales/foto1.jpg'])
  const [activeHeroSlide, setActiveHeroSlide] = useState(0)
  
  const [stats, setStats] = useState({ total_secciones: 4, total_miembros: '120+' })
  
  const [calendarActivities, setCalendarActivities] = useState([])
  const [selectedModalSec, setSelectedModalSec] = useState(null)
  const [modalActivities, setModalActivities] = useState([])
  const [modalLoading, setModalLoading] = useState(false)

  const [galleryImages, setGalleryImages] = useState({ manada: [], tropa: [], comunidad: [], clan: [] })
  const [carouselIndices, setCarouselIndices] = useState({ manada: 0, tropa: 0, comunidad: 0, clan: 0 })
  const [lightbox, setLightbox] = useState({ open: false, key: null, idx: 0 })

  const [botSelection, setBotSelection] = useState(null)

  // ---- EFECTOS ----
  useEffect(() => {
    const fundacion = new Date(2006, 1, 14)
    const hoy = new Date()
    let anos = hoy.getFullYear() - fundacion.getFullYear()
    if (hoy < new Date(hoy.getFullYear(), 1, 14)) anos--
    setYearsOfHistory(anos)

    const handleScroll = () => setScrolled(window.scrollY > 30)
    window.addEventListener('scroll', handleScroll)

    fetch('/api/dashboard')
      .then(r => r.json())
      .then(d => setStats({ total_secciones: d.total_secciones || 4, total_miembros: d.total_miembros || '120+' }))
      .catch(() => {})

    fetch('/api/images/fondos_principales')
      .then(r => r.json())
      .then(data => {
        const apiImgs = (data.imagenes || []).map(i => i.url)
        if (apiImgs.length) setHeroImages(apiImgs)
      })
      .catch(() => {})

    fetch('/api/calendario/proximas')
      .then(r => r.json())
      .then(data => setCalendarActivities(data || []))
      .catch(() => {})

    const seccionesKeys = ['manada', 'tropa', 'comunidad', 'clan']
    seccionesKeys.forEach(key => {
      fetch(`/api/imagenes/${key}`)
        .then(r => r.json())
        .then(data => {
          setGalleryImages(prev => ({ ...prev, [key]: data.imagenes || [] }))
        })
        .catch(() => {})
    })

    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (heroImages.length <= 1) return
    const timer = setInterval(() => {
      setActiveHeroSlide(prev => (prev + 1) % heroImages.length)
    }, 6000)
    return () => clearInterval(timer)
  }, [heroImages])

  useEffect(() => {
    const keys = ['manada', 'tropa', 'comunidad', 'clan']
    const timers = keys.map(key => {
      return setInterval(() => {
        const totalImgs = galleryImages[key]?.length || 0
        if (totalImgs > 1) {
          setCarouselIndices(prev => ({ ...prev, [key]: (prev[key] + 1) % totalImgs }))
        }
      }, 5000)
    })
    return () => timers.forEach(clearInterval)
  }, [galleryImages])

  // ---- ACCIONES ----
  const handleOpenModal = async (key) => {
    setSelectedModalSec(key)
    setModalLoading(true)
    setModalActivities([])
    
    const secData = SECCIONES_CONFIG[key]
    const url = secData.seccionNombre 
      ? `/api/calendario/proximas_seccion?nombre=${encodeURIComponent(secData.seccionNombre)}`
      : `/api/calendario/proximas_seccion`

    try {
      const res = await fetch(url)
      if (res.ok) {
        const acts = await res.json()
        setModalActivities(acts || [])
      }
    } catch (_) {
      setModalActivities([])
    } finally {
      setModalLoading(false)
    }
  }

  const handleCarouselMove = (key, direction) => {
    const total = galleryImages[key]?.length || 0
    if (!total) return
    setCarouselIndices(prev => ({
      ...prev,
      [key]: (prev[key] + direction + total) % total
    }))
  }

  const handleLightboxNav = (direction) => {
    const total = galleryImages[lightbox.key]?.length || 0
    if (!total) return
    setLightbox(prev => ({
      ...prev,
      idx: (prev.idx + direction + total) % total
    }))
  }

  const getColNameBySection = (sec) => {
    if (!sec) return 'grupo'
    const l = sec.toLowerCase()
    if (l.includes('manada')) return 'manada'
    if (l.includes('tropa')) return 'tropa'
    if (l.includes('comunidad') || l.includes('caminante')) return 'comunidad'
    if (l.includes('clan')) return 'clan'
    return 'grupo'
  }

  const groupActivitiesByDate = () => {
    const grouped = {}
    calendarActivities.forEach(act => {
      if (!grouped[act.fecha]) grouped[act.fecha] = []
      grouped[act.fecha].push(act)
    })
    return grouped
  }

  const groupedCalendar = groupActivitiesByDate()

  return (
    <div className="bg-[#faf8f4] text-[#0f1e14] font-sans overflow-x-hidden relative min-h-screen">
      
      {/* NAVIGATION */}
      <nav id="nav" className={`fixed top-0 left-0 right-0 h-[68px] flex items-center justify-between px-[5vw] z-[100] bg-[#faf8f4]/97 backdrop-blur-md border-b border-[#1b4332]/12 transition-all ${scrolled ? 'shadow-[0_6px_28px_rgba(15,30,20,0.1)]' : 'shadow-[0_4px_24px_rgba(15,30,20,0.06)]'}`}>
        <div className="flex items-center gap-2.5">
          <div className="h-11 flex items-center shrink-0">
            <img src="/static/images/grupo/logo_grupo.jpg" alt="Logo Grupo 22" className="h-11 rounded-md object-contain" onError={(e) => e.target.style.display='none'} />
          </div>
          <div className="font-serif text-lg font-bold text-[#1b4332] line-clamp-1">
            Grupo Scout
            <span className="block font-sans text-[11px] font-normal text-[#2d6a4f]/75">22 Quetzalcóatl · Aguascalientes</span>
          </div>
        </div>

        <ul className={`md:flex items-center gap-7 list-none ${mobileNavOpen ? 'flex flex-col absolute top-[68px] left-0 right-0 bg-[#faf8f4]/97 border-b border-[#1b4332]/12 p-5' : 'hidden'}`}>
          <li><a href="#secciones" className="text-sm font-medium text-[#2d6a4f] hover:text-[#1b4332] transition-colors">Secciones</a></li>
          <li><a href="#galeria" className="text-sm font-medium text-[#2d6a4f] hover:text-[#1b4332] transition-colors">Galería</a></li>
          <li><a href="#calendario" className="text-sm font-medium text-[#2d6a4f] hover:text-[#1b4332] transition-colors">Calendario</a></li>
          <li><a href="#contacto" className="text-sm font-medium text-[#2d6a4f] hover:text-[#1b4332] transition-colors">Contacto</a></li>
          <li>
            <button onClick={() => onNavigate('biblioteca')} className="text-sm font-semibold text-[#1b4332] px-5 py-2 rounded-full border-1.5 border-[#1b4332]/28 hover:bg-[#d8f3dc] hover:border-[#40916c] transition-all cursor-pointer bg-transparent">
              📖 Biblioteca
            </button>
          </li>
          <li>
            <button onClick={() => onNavigate('login')} className="text-sm font-semibold bg-[#1b4332] text-white px-5 py-2 rounded-full hover:bg-[#40916c] transition-all shadow-[0_2px_12px_rgba(27,67,50,0.3)] cursor-pointer border-none">
              Intranet →
            </button>
          </li>
        </ul>
        <button className="md:hidden text-2xl text-[#1b4332] bg-none border-none cursor-pointer" onClick={() => setMobileNavOpen(!mobileNavOpen)}>☰</button>
      </nav>

      {/* HERO SECTION */}
      <section id="hero" className="min-h-screen flex flex-col justify-center px-[5vw] pt-[120px] pb-20 relative overflow-hidden bg-[#0f1e14]">
        <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          {heroImages.map((url, i) => (
            <div 
              key={i} 
              className={`absolute inset-0 bg-cover bg-center transition-opacity duration-[1200ms] ease-in-out ${i === activeHeroSlide ? 'opacity-100' : 'opacity-0'}`}
              style={{ backgroundImage: `url('${url}')` }}
            />
          ))}
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a1810]/75 via-[#0a1810]/50 to-[#0a1810]/25 z-10" />
        </div>

        <div className="max-w-[640px] relative z-20 text-white">
          <div className="inline-flex items-center gap-2 bg-white/15 text-white/90 px-3.5 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-7 border border-white/30 backdrop-blur-sm">
            🌿 Scouts de México
          </div>
          <h1 className="font-serif text-5xl md:text-7xl font-black leading-[0.95] mb-6">
            Forja tu<br />
            <em className="text-[#74b494] not-italic">adventure.</em><br />
            Deja tu huella.
          </h1>
          <p className="text-base leading-relaxed text-white/80 max-w-[480px] mb-10">
            Más de 100 años formando líderes a través de la naturaleza, el servicio y la comunidad. Aquí empieza tu historia.
          </p>
          
          <div className="flex gap-3.5 flex-wrap">
            <a href="#contacto" className="bg-[#40916c] hover:bg-[#2d6a4f] text-white px-7 py-3.5 rounded-full font-semibold text-sm transition-all shadow-[0_4px_20px_rgba(27,67,50,0.5)] no-underline">
              🧭 ¡Únete a la Aventura!
            </a>
            <a href="#secciones" className="bg-white/12 border-2 border-white/50 hover:bg-white/22 text-white px-7 py-3.5 rounded-full font-semibold text-sm transition-all backdrop-blur-xs no-underline">
              Encuentra tu Sección →
            </a>
          </div>

          <div className="flex gap-10 mt-16 flex-wrap">
            <div>
              <div className="font-serif text-4xl font-bold">{stats.total_secciones}</div>
              <div className="text-[12px] text-white/65 uppercase tracking-wider font-medium">Secciones activas</div>
            </div>
            <div>
              <div className="font-serif text-4xl font-bold">{stats.total_miembros}</div>
              <div className="text-[12px] text-white/65 uppercase tracking-wider font-medium">Scouts en activo</div>
            </div>
            <div>
              <div className="font-serif text-4xl font-bold">{yearsOfHistory}</div>
              <div className="text-[12px] text-white/65 uppercase tracking-wider font-medium">Años de historia</div>
            </div>
          </div>
        </div>
      </section>

      {/* SECCIONES */}
      <section id="secciones" className="py-24 px-[5vw] bg-white">
        <div className="max-w-[580px] mb-14">
          <div className="inline-flex items-center gap-2 text-xs font-bold tracking-widest uppercase text-[#40916c] mb-3">
            <div className="w-6 h-0.5 bg-[#40916c] rounded-sm" /> Nuestras Secciones
          </div>
          <h2 className="font-serif text-3xl md:text-5xl font-bold text-[#0f1e14] leading-tight">Un lugar para cada edad, un reto para cada momento</h2>
          <p className="mt-4 text-[#3a5c43] leading-relaxed">Nuestro programa está diseñado por etapas de vida. Cada sección tiene su propio marco simbólico, sus retos y su espíritu.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {['manada', 'tropa', 'comunidad', 'clan'].map((key) => {
            const sec = SECCIONES_CONFIG[key]
            return (
              <div key={key} onClick={() => handleOpenModal(key)} className="rounded-[20px] overflow-hidden border border-[#1b4332]/12 hover:-translate-y-1.5 hover:shadow-[0_16px_48px_rgba(15,30,20,0.14)] transition-all cursor-pointer bg-[#faf8f4]">
                <div className={`h-[200px] flex items-center justify-center bg-gradient-to-br ${sec.bgGradient} p-4`}>
                  <span className="text-7xl">{sec.emoji}</span>
                </div>
                <div className="p-[22px]">
                  <h3 className="font-serif text-xl font-bold text-[#0f1e14] mb-2">{sec.title}</h3>
                  <div className="inline-flex items-center gap-1.5 bg-[#d8f3dc] text-[#2d6a4f] px-3 py-1 rounded-full text-xs font-semibold mb-3">
                    🎂 {sec.subtitle}
                  </div>
                  <p className="text-xs text-[#4a6651] line-clamp-3 leading-relaxed">{sec.marco}</p>
                  <div className="inline-flex items-center gap-1.5 mt-4 text-xs font-bold text-[#40916c]">
                    Conocer más <span>→</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* GALERÍA */}
      <section id="galeria" className="py-24 bg-[#0f1e14]">
        <div className="px-[5vw] mb-14">
          <div className="text-xs font-bold tracking-widest uppercase text-[#74b494] mb-3 flex items-center gap-2">
            <div className="w-6 h-0.5 bg-[#74b494]" /> Nuestras Actividades
          </div>
          <h2 className="font-serif text-3xl md:text-5xl font-bold text-white">Galería por sección</h2>
          <p className="text-white/55 max-w-[520px] leading-relaxed text-sm mt-3">Momentos reales de campamentos, reuniones y proyectos de servicio. Una foto a la vez.</p>
        </div>

        {['manada', 'tropa', 'comunidad', 'clan'].map((key) => {
          const sec = SECCIONES_CONFIG[key]
          const imgs = galleryImages[key] || []
          const activeIdx = carouselIndices[key]
          
          return (
            <div key={key} className="px-[5vw] pb-16 last:pb-0">
              <div className="flex items-center gap-3.5 mb-6">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: sec.color }} />
                <h3 className="font-serif text-xl font-bold text-white">{sec.title}</h3>
                <span className="text-xs text-white/35 ml-auto font-medium">{imgs.length} fotos</span>
              </div>

              <div className="relative group/carousel">
                <div className="relative rounded-[20px] overflow-hidden aspect-video bg-white/5 border border-white/8">
                  {imgs.length === 0 ? (
                    <div className="w-full h-full flex flex-col items-center justify-center gap-3 bg-[repeating-linear-gradient(45deg,rgba(255,255,255,0.03)_0px,rgba(255,255,255,0.03)_10px,transparent_10px,transparent_20px)]">
                      <span className="text-4xl opacity-30">📷</span>
                      <span className="text-xs text-white/25 font-mono">// fotos de {sec.title.toLowerCase()} aquí</span>
                    </div>
                  ) : (
                    <>
                      <div className="flex h-full transition-transform duration-500 ease-out" style={{ transform: `translateX(-${activeIdx * 100}%)` }}>
                        {imgs.map((img, i) => (
                          <div key={i} className="min-w-full h-full relative cursor-zoom-in" onClick={() => setLightbox({ open: true, key, idx: i })}>
                            <img src={img.url} alt={img.nombre || sec.title} className="w-full h-full object-cover" />
                            {img.nombre && <div className="absolute bottom-0 left-0 right-0 p-6 pt-10 bg-gradient-to-t from-black/65 text-white text-xs">{img.nombre}</div>}
                          </div>
                        ))}
                      </div>
                      <div className="absolute top-3.5 right-3.5 bg-black/50 text-white/70 text-[11px] font-semibold px-2.5 py-1 rounded-full backdrop-blur-xs">
                        {activeIdx + 1} / {imgs.length}
                      </div>
                    </>
                  )}
                </div>

                {imgs.length > 1 && (
                  <>
                    <button className="absolute top-1/2 left-3.5 -translate-y-1/2 w-11 h-11 rounded-full bg-black/50 border border-white/20 text-white text-lg cursor-pointer flex items-center justify-center hover:bg-black/80 md:opacity-0 group-hover/carousel:opacity-100 transition-opacity" onClick={() => handleCarouselMove(key, -1)}>‹</button>
                    <button className="absolute top-1/2 right-3.5 -translate-y-1/2 w-11 h-11 rounded-full bg-black/50 border border-white/20 text-white text-lg cursor-pointer flex items-center justify-center hover:bg-black/80 md:opacity-0 group-hover/carousel:opacity-100 transition-opacity" onClick={() => handleCarouselMove(key, 1)}>›</button>
                    <div className="flex justify-center gap-1.5 mt-3.5">
                      {imgs.map((_, i) => (
                        <button key={i} className={`w-1.5 h-1.5 rounded-full transition-all border-none p-0 cursor-pointer ${i === activeIdx ? 'bg-[#74b494] w-5 rounded-sm' : 'bg-white/25'}`} onClick={() => setCarouselIndices(p => ({ ...p, [key]: i }))} />
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </section>

      {/* CALENDARIO */}
      <section id="calendario" className="py-24 px-[5vw] bg-[#f5ede4]">
        <div className="max-w-4xl mx-auto">
          <div className="text-xs font-bold tracking-widest uppercase text-[#40916c] mb-3 flex items-center gap-2">
            <div className="w-6 h-0.5 bg-[#40916c]" /> Próximas Actividades
          </div>
          <h2 className="font-serif text-3xl md:text-5xl font-bold text-[#0f1e14]">Lo que viene en el grupo</h2>
          <p className="text-[#3a5c43] text-sm mt-3 font-medium">Agenda unificada para los próximos 30 días</p>

          <div className="mt-12 overflow-x-auto rounded-[20px] shadow-[0_4px_32px_rgba(15,30,20,0.1)]">
            <table className="w-full border-collapse bg-white min-w-[680px]">
              <thead>
                <tr className="text-xs uppercase font-bold tracking-wider text-center border-b-3 border-black/5">
                  <th className="p-4 bg-[#fef9e7] text-[#7d6608] w-[110px]">Día</th>
                  <th className="p-4 bg-[#fef3c7] text-[#92400e]">🐺 Manada</th>
                  <th className="p-4 bg-[#dcfce7] text-[#166534]">⛺ Tropa</th>
                  <th className="p-4 bg-[#cffafe] text-[#155e75]">🥾 Comunidad</th>
                  <th className="p-4 bg-[#fee2e2] text-[#991b1b]">🔥 Clan</th>
                </tr>
              </thead>
              <tbody>
                {calendarActivities.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="p-12 text-center text-[#2d6a4f] text-sm">
                      Sin actividades programadas en puerta. ¡Consulta la intranet para más detalles!
                    </td>
                  </tr>
                ) : (
                  Object.keys(groupedCalendar).sort().map(fecha => {
                    const items = groupedCalendar[fecha]
                    const d = new Date(fecha + 'T12:00:00')
                    const globalAct = items.find(a => !a.seccion || a.seccion === 'Todo el Grupo')
                    
                    return (
                      <tr key={fecha} className="border-b border-black/5 last:border-none hover:bg-black/5">
                        <td className="p-4 text-center font-serif font-bold text-[#1b4332] bg-[#fef9e7] border-r-2 border-black/5">
                          <div className="text-2xl leading-none">{String(d.getDate()).padStart(2, '0')}</div>
                          <div className="text-[10px] uppercase tracking-wider text-[#40916c] font-sans mt-0.5">{MESES_CORTO[d.getMonth()]}</div>
                          <div className="text-[10px] text-gray-400 font-sans font-normal">{DIAS_SEMANA[d.getDay()]}</div>
                        </td>

                        {globalAct ? (
                          <td colSpan="4" className="p-3.5 text-center">
                            <div className="bg-gradient-to-r from-[#ede9fe] to-[#ddd6fe] text-[#4c1d95] rounded-xl p-3 font-bold text-sm">
                              {globalAct.titulo}
                              {globalAct.descripcion && <div className="text-xs font-normal opacity-75 mt-1">{globalAct.descripcion}</div>}
                            </div>
                          </td>
                        ) : (
                          ['manada', 'tropa', 'comunidad', 'clan'].map(col => {
                            const matchingActs = items.filter(a => getColNameBySection(a.seccion) === col)
                            return (
                              <td key={col} className={`p-3 text-center align-middle ${matchingActs.length === 0 ? 'bg-black/5' : ''}`}>
                                {matchingActs.map((a, idx) => (
                                  <div key={idx} className={`rounded-xl p-2.5 text-xs font-bold leading-snug w-full mb-1 last:mb-0 text-left ${col === 'manada' ? 'bg-[#fef3c7] text-[#92400e]' : col === 'tropa' ? 'bg-[#dcfce7] text-[#166534]' : col === 'comunidad' ? 'bg-[#cffafe] text-[#155e75]' : 'bg-[#fee2e2] text-[#991b1b]'}`}>
                                    <div>{a.titulo}</div>
                                    {(a.lugar || a.hora) && (
                                      <div className="text-[10px] font-normal opacity-80 mt-1">
                                        {[a.hora ? `${a.hora} hrs` : '', a.lugar ? `📍 ${a.lugar}` : ''].filter(Boolean).join(' · ')}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </td>
                            )
                          })
                        )}
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CONTACTO & BOT */}
      <section id="contacto" className="py-24 px-[5vw] bg-white">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-14 max-w-5xl mx-auto items-start">
          <div>
            <div className="text-xs font-bold tracking-widest uppercase text-[#40916c] mb-3 flex items-center gap-2">
              <div className="w-6 h-0.5 bg-[#40916c]" /> Contacto
            </div>
            <h2 className="font-serif text-3xl md:text-4xl font-bold leading-tight mb-4">¿Listo para unirte a la aventura?</h2>
            <p className="text-[#3a5c43] leading-relaxed text-sm">Cuéntanos qué edad tiene tu hijo o hija y nuestro guardián digital te enlazará directo con el scouter encargado.</p>
            
            <div className="flex items-start gap-3.5 mt-7">
              <div className="w-11 h-11 rounded-xl bg-[#d8f3dc] flex items-center justify-center text-xl shrink-0">📍</div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#40916c] mb-0.5">Ubicación</div>
                <div className="text-sm font-medium">Av Canal Interceptor 91, Aguascalientes, Ags.</div>
              </div>
            </div>
            <div className="flex items-start gap-3.5 mt-6">
              <div className="w-11 h-11 rounded-xl bg-[#d8f3dc] flex items-center justify-center text-xl shrink-0">📅</div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#40916c] mb-0.5">Reuniones</div>
                <div className="text-sm font-medium">Sábados · 4pm a 6:30pm</div>
              </div>
            </div>
          </div>

          <div className="bg-[#faf8f4] rounded-[20px] border border-[#1b4332]/12 overflow-hidden shadow-[0_4px_24px_rgba(15,30,20,0.07)]">
            <div className="bg-[#1b4332] text-white p-5 px-6 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full overflow-hidden shrink-0">
                <img src="/static/images/grupo/quetzi.jpg" alt="Quetzi" className="w-full h-full object-cover" />
              </div>
              <div>
                <div className="font-bold text-sm">Quetzi</div>
                <div className="text-[11px] opacity-60"><span className="inline-block w-2 h-2 rounded-full bg-[#4ade80] mr-1.5" />En línea ahora</div>
              </div>
            </div>

            <div className="p-5 flex flex-col gap-3.5 min-h-[260px]">
              <div className="bg-white p-3 px-4 rounded-2xl rounded-bl-xs text-sm border border-[#1b4332]/12 max-w-[85%] self-start">
                ¡Hola! 👋 Soy Quetzi, el guardián del <strong>Grupo Scout 22 Quetzalcóatl</strong>. ¿Para qué rango de edad buscas información?
              </div>

              {!botSelection ? (
                <div className="flex flex-col gap-2 max-w-[85%]">
                  <button onClick={() => setBotSelection('manada')} className="bg-white border border-[#40916c] text-[#40916c] p-2 px-3.5 rounded-full text-xs font-semibold cursor-pointer text-center hover:bg-[#40916c] hover:text-white transition-all">🐺 Manada · 6 a 10 años</button>
                  <button onClick={() => setBotSelection('tropa')} className="bg-white border border-[#40916c] text-[#40916c] p-2 px-3.5 rounded-full text-xs font-semibold cursor-pointer text-center hover:bg-[#40916c] hover:text-white transition-all">⛺ Tropa Scout · 10 a 14 años</button>
                  <button onClick={() => setBotSelection('comunidad')} className="bg-white border border-[#40916c] text-[#40916c] p-2 px-3.5 rounded-full text-xs font-semibold cursor-pointer text-center hover:bg-[#40916c] hover:text-white transition-all">🥾 Comunidad · 14 a 17 años</button>
                  <button onClick={() => setBotSelection('clan')} className="bg-white border border-[#40916c] text-[#40916c] p-2 px-3.5 rounded-full text-xs font-semibold cursor-pointer text-center hover:bg-[#40916c] hover:text-white transition-all">🔥 Clan Rover · 17 a 21 años</button>
                  <button onClick={() => setBotSelection('jefeGrupo')} className="bg-white border border-[#40916c] text-[#40916c] p-2 px-3.5 rounded-full text-xs font-semibold cursor-pointer text-center hover:bg-[#40916c] hover:text-white transition-all">⚜️ Jefe de Grupo · General</button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-white p-3 px-4 rounded-2xl rounded-bl-xs text-sm border border-[#1b4332]/12 max-w-[85%] self-start">
                    ¡Perfecto! 🎉 Te conecto con <strong>{SECCIONES_CONFIG[botSelection].jefe}</strong>, responsable de la sección.
                  </div>
                  <div className="p-4 pt-0">
                    <button 
                      onClick={() => window.open(`https://wa.me/52${SECCIONES_CONFIG[botSelection].telefono}?text=${encodeURIComponent(SECCIONES_CONFIG[botSelection].msg)}`, '_blank')}
                      className="flex items-center justify-center gap-2.5 bg-[#25D366] text-white p-3.5 rounded-full font-bold text-sm cursor-pointer hover:bg-[#1fba58] transition-all w-full border-none"
                    >
                      💬 Chatear con {SECCIONES_CONFIG[botSelection].jefe}
                    </button>
                    <button onClick={() => setBotSelection(null)} className="text-xs text-[#2d6a4f] bg-transparent border-none cursor-pointer mt-3 block mx-auto font-medium">
                      ← Cambiar selección
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* UBICACION */}
      <section id="ubicacion" className="py-24 px-[5vw] bg-[#1b4332] text-white">
        <div className="inline-flex items-center gap-2 text-xs font-bold tracking-widest uppercase text-[#74b494] mb-3">
          <div className="w-6 h-0.5 bg-[#74b494]" /> Cómo Llegar
        </div>
        <h2 className="font-serif text-3xl md:text-5xl font-bold mb-3">Nuestro local de grupo</h2>
        <p className="text-white/65 max-w-[520px] text-sm">Nos reunimos los sábados. ¡Las familias nuevas son bienvenidas a participar en la primera sesión de juego!</p>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12 items-start">
          <div className="lg:col-span-2">
            <div className="rounded-[20px] overflow-hidden h-[340px] border border-white/15 relative shadow-[0_8px_40px_rgba(0,0,0,0.3)]">
              <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1m4!2s0x8429ee628bbfebed%3A0x6bba3c1b69eb070c!2sAv.+Canal+Interceptor+91%2C+San+Cayetano%2C+20130+Aguascalientes%2C+Ags.!5e0!3m2!1ses-419!2smx!4v1715420000000!5m2!1ses-419!2smx" className="w-full h-full border-0 block" allowFullScreen="" loading="lazy" referrerPolicy="no-referrer-when-downgrade" title="Ubicación Grupo 22"></iframe>
            </div>
          </div>
          <div className="flex flex-col gap-5">
            <div className="bg-white/10 border border-white/10 rounded-xl p-5 flex gap-3.5">
              <div className="text-2xl">🏫</div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#74b494] mb-1">Local</div>
                <div className="text-xs text-white/85 leading-relaxed">Av Canal Interceptor 91<br />San Cayetano, 20130 Aguascalientes.</div>
              </div>
            </div>
            <div className="bg-white/10 border border-white/10 rounded-xl p-5 flex gap-3.5">
              <div className="text-2xl">🚌</div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#74b494] mb-1">Camiones</div>
                <div className="text-xs text-white/85">Rutas: 4, 11, 15, 19, 28, 30, 33, 38 y 40.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-[#0f1e14] text-white/55 px-[5vw] py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 pb-10 border-b border-white/10">
          <div>
            <div className="font-serif text-lg font-bold text-white/85 mb-3">Grupo Scout 22</div>
            <p className="text-xs leading-relaxed max-w-[280px]">Formando ciudadanos comprometidos en Aguascalientes desde hace {yearsOfHistory} años.</p>
          </div>
          <div>
            <h4 className="font-serif text-sm font-bold text-white/85 mb-3.5">Secciones</h4>
            <ul className="list-none space-y-2 text-xs p-0 m-0">
              <li>Manada (6-10 años)</li>
              <li>Trophy Omeyocan (10-14 años)</li>
              <li>Comunidad (14-17 años)</li>
              <li>Clan Rover (18-21 años)</li>
            </ul>
          </div>
          <div>
            <h4 className="font-serif text-sm font-bold text-white/85 mb-3.5">Enlaces</h4>
            <ul className="list-none space-y-2 text-xs p-0 m-0">
              <li><a href="#galeria" className="hover:text-[#74b494]">Galería de Fotos</a></li>
              <li><a href="#calendario" className="hover:text-[#74b494]">Calendario Semanal</a></li>
              <li><button onClick={() => onNavigate('biblioteca')} className="hover:text-[#74b494] bg-transparent border-none p-0 text-left cursor-pointer text-white/55 font-sans text-xs">Biblioteca Digital →</button></li>
            </ul>
          </div>
          <div>
            <h4 className="font-serif text-sm font-bold text-white/85 mb-3.5">Organización</h4>
            <div className="text-xs">Provincia Aguascalientes<br />Scouts de México A.C.</div>
          </div>
        </div>
        <div className="flex justify-between flex-wrap gap-3 pt-6 text-[11px]">
          <span>© 2026 Grupo Scout 22 Quetzalcóatl — Todos los derechos reservados.</span>
        </div>
      </footer>

      {/* LIGHTBOX OVERLAY */}
      {lightbox.open && (
        <div className="fixed inset-0 z-[300] bg-black/92 backdrop-blur-md flex items-center justify-center" onClick={() => setLightbox({ open: false, key: null, idx: 0 })}>
          <button className="absolute top-5 right-5 w-11 h-11 rounded-full bg-white/12 border border-white/20 text-white text-xl cursor-pointer flex items-center justify-center hover:bg-white/25">✕</button>
          {galleryImages[lightbox.key]?.length > 1 && (
            <>
              <button className="absolute top-1/2 left-5 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 border border-white/20 text-white text-2xl cursor-pointer flex items-center justify-center hover:bg-white/20" onClick={(e) => { e.stopPropagation(); handleLightboxNav(-1); }}>‹</button>
              <button className="absolute top-1/2 right-5 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 border border-white/20 text-white text-2xl cursor-pointer flex items-center justify-center hover:bg-white/20" onClick={(e) => { e.stopPropagation(); handleLightboxNav(1); }}>›</button>
            </>
          )}
          <img src={galleryImages[lightbox.key]?.[lightbox.idx]?.url} alt="Zoom" className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-[0_24px_80px_rgba(0,0,0,0.6)]" onClick={(e) => e.stopPropagation()} />
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/55 text-xs">
            {galleryImages[lightbox.key]?.[lightbox.idx]?.nombre || ''} — {lightbox.idx + 1} / {galleryImages[lightbox.key]?.length}
          </div>
        </div>
      )}

      {/* SECCIÓN MODAL DETALLES */}
      {selectedModalSec && (
        <div className="fixed inset-0 z-[200] bg-[#0f1e14]/50 backdrop-blur-xs flex items-center justify-center p-5" onClick={() => setSelectedModalSec(null)}>
          <div className="bg-[#faf8f4] rounded-[24px] w-full max-w-[720px] max-h-[90vh] overflow-y-auto shadow-[0_24px_80px_rgba(15,30,20,0.25)]" onClick={(e) => e.stopPropagation()}>
            <div className={`h-[160px] flex items-center justify-center relative rounded-t-[24px] bg-gradient-to-br ${SECCIONES_CONFIG[selectedModalSec].bgGradient}`}>
              <button className="absolute top-4 right-4 w-9 h-9 rounded-full bg-white/80 border-none cursor-pointer text-lg flex items-center justify-center" onClick={() => setSelectedModalSec(null)}>✕</button>
              <span className="text-7xl">{SECCIONES_CONFIG[selectedModalSec].emoji}</span>
            </div>
            <div className="p-8">
              <h3 className="text-3xl font-bold text-[#1b4332] mb-1">{SECCIONES_CONFIG[selectedModalSec].title}</h3>
              <div className="text-[#2d6a4f] text-sm mb-5 font-medium">🎂 Rango: {SECCIONES_CONFIG[selectedModalSec].subtitle}</div>
              
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#40916c] mb-3">Marco Simbólico</div>
              <p className="text-sm text-[#3a5c43] leading-relaxed mb-6">{SECCIONES_CONFIG[selectedModalSec].marco}</p>
              
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#40916c] mb-3">Próximas Actividades</div>
              <div className="space-y-2.5">
                {modalLoading ? (
                  <div className="text-xs text-[#2d6a4f] opacity-60 p-4 text-center">Cargando agenda oficial...</div>
                ) : modalActivities.length === 0 ? (
                  <div className="p-4 text-center text-[#2d6a4f]/70 text-xs border border-dashed border-[#2d6a4f]/20 rounded-xl">Sin actividades calendarizadas esta semana.</div>
                ) : (
                  modalActivities.map((a, idx) => {
                    const actDate = new Date(a.fecha + 'T12:00:00')
                    return (
                      <div key={idx} className="flex items-center gap-3.5 bg-white border border-[#1b4332]/12 rounded-xl p-3 px-4">
                        <div className="min-w-[44px] text-center bg-[#d8f3dc] rounded-lg p-1.5">
                          <div className="font-serif text-lg font-bold text-[#1b4332] leading-none">{actDate.getDate()}</div>
                          <div className="text-[9px] uppercase font-bold text-[#40916c]">{MESES_CORTO[actDate.getMonth()]}</div>
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{a.titulo}</div>
                          {a.lugar && <div className="text-xs text-[#2d6a4f]">📍 {a.lugar}</div>}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              <button 
                onClick={() => window.open(`https://wa.me/52${SECCIONES_CONFIG[selectedModalSec].telefono}?text=${encodeURIComponent(SECCIONES_CONFIG[selectedModalSec].msg)}`, '_blank')}
                className="inline-flex items-center gap-2.5 bg-[#25D366] text-white px-6 py-3 rounded-full font-bold text-sm mt-6 border-none cursor-pointer hover:bg-[#1fba58] transition-all"
              >
                Contactar al Jefe: {SECCIONES_CONFIG[selectedModalSec].jefe}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}