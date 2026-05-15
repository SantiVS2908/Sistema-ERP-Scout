import React, { useState, useEffect } from 'react'

export const Miembros = ({ user }) => {
  // ---- ESTADOS (React State) ----
  const [miembros, setMiembros] = useState([])
  const [secciones, setSecciones] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Estados para los filtros exactos de tu código viejo
  const [search, setSearch] = useState('')
  const [seccionFiltro, setSeccionFiltro] = useState('')
  const [activoFiltro, setActivoFiltro] = useState('true')

  // ---- CARGAR DATOS DE LA API ----
  const cargarMiembros = () => {
    setLoading(true)
    
    // Construimos la URL con los filtros tal cual tu función loadMiembros() vieja
    let url = `/api/miembros?activo=${activoFiltro}`
    if (search.trim()) url += `&q=${encodeURIComponent(search)}`
    if (seccionFiltro) url += `&seccion_id=${seccionFiltro}`
    
    // Si el usuario no es master/dev, la API o el frontend restringen a su sección
    const esMaster = user?.rol === 'master' || user?.rol === 'dev'
    if (!esMaster && user?.seccion_id) {
      url += `&seccion_id=${user.seccion_id}`
    }

    const token = sessionStorage.getItem('scout_token')
    
    fetch(url, {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.json())
      .then(data => setMiembros(data || []))
      .catch(err => console.error("Error al cargar miembros:", err))
      .finally(() => setLoading(false))
  }

  // Cargar secciones para el dropdown de filtro
  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    fetch('/api/secciones', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.json())
      .then(data => setSecciones(data || []))
      .catch(err => console.error("Error al cargar secciones:", err))
  }, [])

  // Ejecutar la búsqueda cada vez que cambien los filtros
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      cargarMiembros()
    }, 300) // Un pequeño delay de 300ms al escribir para no saturar Postgres
    return () => clearTimeout(delayDebounce)
  }, [search, seccionFiltro, activoFiltro])

  // Helper para calcular edad (Tu misma lógica vieja)
  const calcEdad = (fn) => {
    if (!fn) return '—'
    const nac = new Date(fn + 'T12:00:00')
    const hoy = new Date()
    return hoy.getFullYear() - nac.getFullYear() - ((hoy.getMonth() < nac.getMonth() || (hoy.getMonth() === nac.getMonth() && hoy.getDate() < nac.getDate())) ? 1 : 0)
  }

  const esJefe = user?.rol === 'master' || user?.rol === 'dev' || user?.rol === 'jefe_seccion'

  return (
    <div className="space-y-6">
      
      {/* BARRA DE FILTROS (MIGRADA DE TU CLASS="FILTERS") */}
      <div className="bg-white p-4 border border-[#c8dcc8] rounded-xl flex flex-wrap gap-3 items-center shadow-[0_2px_12px_rgba(27,67,50,0.05)]">
        <input 
          type="text" 
          className="p-2 px-4 bg-[#faf8f4] border border-[#c8dcc8] rounded-lg text-sm outline-none focus:border-[#52b788] min-w-[220px] flex-1 sm:flex-none"
          placeholder="🔍 Buscar por nombre o número..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select 
          className="p-2 bg-white border border-[#c8dcc8] rounded-lg text-sm outline-none focus:border-[#52b788]"
          value={seccionFiltro}
          onChange={(e) => setSeccionFiltro(e.target.value)}
          disabled={user?.rol !== 'master' && user?.rol !== 'dev'} // Bloqueado si es jefe de sección común
        >
          <option value="">Todas las secciones</option>
          {secciones.map(s => (
            <option key={s.id} value={s.id}>{s.nombre}</option>
          ))}
        </select>

        <select 
          className="p-2 bg-white border border-[#c8dcc8] rounded-lg text-sm outline-none focus:border-[#52b788]"
          value={activoFiltro}
          onChange={(e) => setActivoFiltro(e.target.value)}
        >
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
          <option value="">Todos</option>
        </select>

        {esJefe && (
          <button className="ml-auto bg-[#40916c] hover:bg-[#2d6a4f] text-white text-xs font-bold p-2.5 px-4 rounded-lg transition-colors cursor-pointer border-none">
            + Nuevo miembro
          </button>
        )}
      </div>

      {/* CONTENEDOR DE LA TABLA / CARDS */}
      <div className="bg-white border border-[#c8dcc8] rounded-xl shadow-[0_2px_12px_rgba(27,67,50,0.05)] overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-[#2d6a4f] font-medium">
            ⏳ Consultando registros en Postgres...
          </div>
        ) : miembros.length === 0 ? (
          <div className="p-12 text-center text-gray-400 italic">
            Sin miembros registrados que coincidan con los filtros.
          </div>
        ) : (
          <div className="overflow-x-auto">
            {/* VISTA DESKTOP: TABLA CLÁSICA */}
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="bg-[#f0f5f1] border-b border-[#c8dcc8] text-[11px] font-bold text-[#2d6a4f] uppercase tracking-wider">
                  <th className="p-3.5 px-4 font-mono">Nº Scout</th>
                  <th className="p-3.5 px-4">Nombre</th>
                  <th className="p-3.5 px-4">Sección</th>
                  <th className="p-3.5 px-4">Cargo</th>
                  <th className="p-3.5 px-4">Edad</th>
                  <th className="p-3.5 px-4">Estado</th>
                  {esJefe && <th className="p-3.5 px-4 text-right">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e0ece0]">
                {miembros.map(m => {
                  const edad = calcEdad(m.fecha_nacimiento)
                  return (
                    <tr key={m.id} className="hover:bg-[#f5fbf6] transition-colors cursor-pointer">
                      <td className="p-4 px-4 font-mono text-xs text-gray-400">{m.numero_scout || '—'}</td>
                      <td className="p-4 px-4 font-bold text-[#0f1e14]">
                        {m.apellido}, {m.nombre}
                        {m.tipo === 'scouter' ? (
                          <span className="ml-2 bg-[#e0f0ff] text-[#1a5276] text-[10px] px-2 py-0.5 rounded-full">👤 Scouter</span>
                        ) : (
                          <span className="ml-2 bg-[#e8f8f5] text-[#117a65] text-[10px] px-2 py-0.5 rounded-full">🧒 Benef.</span>
                        )}
                      </td>
                      <td className="p-4 px-4">
                        <span className="inline-flex anonymity items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full" style={{ background: m.seccion_color || '#ccc' }} />
                          {m.seccion_nombre || '—'}
                        </span>
                      </td>
                      <td className="p-4 px-4 text-gray-600">{m.cargo || '—'}</td>
                      <td className="p-4 px-4 text-gray-600">{edad} {edad !== '—' ? 'años' : ''}</td>
                      <td className="p-4 px-4">
                        <span className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full ${m.activo ? 'bg-[#d8f3dc] text-[#1b4332]' : 'bg-gray-100 text-gray-500'}`}>
                          {m.activo ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      {esJefe && (
                        <td className="p-4 px-4 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                          <button className="bg-[#faf8f4] hover:bg-[#f0f5f1] text-gray-700 border border-[#c8dcc8] text-xs font-semibold py-1 px-2.5 rounded-md cursor-pointer transition-colors">✎</button>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}