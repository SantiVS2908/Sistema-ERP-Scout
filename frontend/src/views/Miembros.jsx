import React, { useState, useEffect } from 'react'

export const Miembros = ({ user }) => {
  // ---- ESTADOS (React State) ----
  const [miembros, setMiembros] = useState([])
  const [secciones, setSecciones] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Filtros de búsqueda
  const [search, setSearch] = useState('')
  const [seccionFiltro, setSeccionFiltro] = useState('')
  const [activoFiltro, setActivoFiltro] = useState('true')

  // Estados para el Formulario Modal (Altas / Ediciones)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editandoId, setEditandoId] = useState(null) // null = Crear, string = Editar
  const [formData, setFormData] = useState({
    numero_scout: '', nombre: '', apellido: '', tipo: 'beneficiario',
    fecha_nacimiento: '', cargo: '', seccion_id: '', telefono: '',
    email: '', direccion: '', nombre_tutor: '', telefono_emergencia: '',
    grupo_sanguineo: '', alergias: '', notas: '', activo: true
  })

  // ---- CARGAR DATOS DE LA API ----
  const cargarMiembros = () => {
    setLoading(true)
    let url = `/api/miembros?activo=${activoFiltro}`
    if (search.trim()) url += `&q=${encodeURIComponent(search)}`
    if (seccionFiltro) url += `&seccion_id=${seccionFiltro}`
    
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

  // Cargar secciones para los dropdowns
  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    fetch('/api/secciones', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.json())
      .then(data => setSecciones(data || []))
      .catch(err => console.error("Error al cargar secciones:", err))
  }, [])

  // Escuchar cambios en los filtros principales
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      cargarMiembros()
    }, 300)
    return () => clearTimeout(delayDebounce)
  }, [search, seccionFiltro, activoFiltro])

  // Helper para calcular edad
  const calcEdad = (fn) => {
    if (!fn) return '—'
    const nac = new Date(fn + 'T12:00:00')
    const hoy = new Date()
    return hoy.getFullYear() - nac.getFullYear() - ((hoy.getMonth() < nac.getMonth() || (hoy.getMonth() === nac.getMonth() && hoy.getDate() < nac.getDate())) ? 1 : 0)
  }

  // ---- CONTROLADORES DEL FORMULARIO ----
  const abrirModalNuevo = () => {
    setEditandoId(null)
    setFormData({
      numero_scout: '', nombre: '', apellido: '', tipo: 'beneficiario',
      fecha_nacimiento: '', cargo: '', seccion_id: seccionFiltro || '', telefono: '',
      email: '', direccion: '', nombre_tutor: '', telefono_emergencia: '',
      grupo_sanguineo: '', alergias: '', notas: '', activo: true
    })
    setModalAbierto(true)
  }

  const abrirModalEditar = (m) => {
    setEditandoId(m.id)
    setFormData({
      numero_scout: m.numero_scout || '',
      nombre: m.nombre || '',
      apellido: m.apellido || '',
      tipo: m.tipo || 'beneficiario',
      fecha_nacimiento: m.fecha_nacimiento || '',
      cargo: m.cargo || '',
      seccion_id: m.seccion_id || '',
      telefono: m.telefono || '',
      email: m.email || '',
      direccion: m.direccion || '',
      nombre_tutor: m.nombre_tutor || '',
      telefono_emergencia: m.telefono_emergencia || '',
      grupo_sanguineo: m.grupo_sanguineo || '',
      alergias: m.alergias || '',
      notes: m.notas || '',
      activo: m.activo ?? true
    })
    setModalAbierto(true)
  }

  const manejarCambioInput = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const guardarMiembro = (e) => {
    e.preventDefault()
    const token = sessionStorage.getItem('scout_token')
    
    const url = editandoId ? `/api/miembros/${editandoId}` : '/api/miembros'
    const metodo = editandoId ? 'PUT' : 'POST'

    fetch(url, {
      method: metodo,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify(formData)
    })
      .then(r => {
        if (!r.ok) return r.json().then(err => { throw err })
        return r.json()
      })
      .then((data) => {
        setModalAbierto(false)
        cargarMiembros() // Refresca la lista en Postgres en tiempo real

        // 👁️ SI EL BACKEND GENERÓ CREDENCIALES, DETIENE LA INTERFAZ Y LAS MUESTRA:
        if (data.credenciales) {
          alert(
            `📢 ¡CUENTA DE SCOUTER GENERADA CON ÉXITO!\n\n` +
            `Nombre: ${formData.nombre} ${formData.apellido}\n` +
            `Usuario: ${data.credenciales.username}\n` +
            `Correo: ${data.credenciales.email}\n` +
            `Contraseña Temporal: ${data.credenciales.password_temporal || 'Password123'}\n\n` +
            `👉 Asegúrate de copiar estos accesos antes de cerrar este aviso.`
          )
        }
      })
      .catch(err => {
        alert("Error al procesar la solicitud: " + (err.detail || JSON.stringify(err)))
      })
  }

  const esJefe = user?.rol === 'master' || user?.rol === 'dev' || user?.rol === 'jefe_seccion'

  return (
    <div className="space-y-6">
      
      {/* BARRA DE FILTROS */}
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
          disabled={user?.rol !== 'master' && user?.rol !== 'dev'}
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
          <button 
            onClick={abrirModalNuevo}
            className="ml-auto bg-[#40916c] hover:bg-[#2d6a4f] text-white text-xs font-bold p-2.5 px-4 rounded-lg transition-colors cursor-pointer border-none"
          >
            + Nuevo miembro
          </button>
        )}
      </div>

      {/* TABLA PRINCIPAL */}
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
                        <span className="inline-flex items-center gap-1.5">
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
                        <td className="p-4 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button 
                            onClick={() => abrirModalEditar(m)}
                            className="bg-[#faf8f4] hover:bg-[#f0f5f1] text-gray-700 border border-[#c8dcc8] text-xs font-semibold py-1 px-2.5 rounded-md cursor-pointer transition-colors"
                          >
                            ✎ Editar
                          </button>
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

      {/* MODAL INTEGRADO CON COMPATIBILIDAD FASTAPI / POSTGRES */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-xl border border-[#c8dcc8] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-fade-in">
            <div className="p-5 border-b border-[#e0ece0] flex justify-between items-center bg-[#f0f5f1]">
              <h3 className="font-serif font-bold text-[#1b4332] text-lg">
                {editandoId ? '📝 Editar Información del Scout' : '⚜️ Registrar Nuevo Miembro'}
              </h3>
              <button onClick={() => setModalAbierto(false)} className="text-gray-400 hover:text-gray-600 text-xl border-none bg-transparent cursor-pointer">×</button>
            </div>

            <form onSubmit={guardarMiembro} className="p-6 space-y-4 text-sm text-left">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Nombre *</label>
                  <input type="text" name="nombre" required value={formData.nombre} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Apellido(s) *</label>
                  <input type="text" name="apellido" required value={formData.apellido} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Número de Credencial Scout</label>
                  <input type="text" name="numero_scout" value={formData.numero_scout} onChange={manejarCambioInput} placeholder="Ej. MX1234" className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Tipo de Registro *</label>
                  <select name="tipo" value={formData.tipo} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg bg-white outline-none focus:border-[#52b788]">
                    <option value="beneficiario">Beneficiario (Muchacho)</option>
                    <option value="scouter">Scouter (Adulto / Dirigente)</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Sección Asignada *</label>
                  <select name="seccion_id" required value={formData.seccion_id} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg bg-white outline-none focus:border-[#52b788]">
                    <option value="">Selecciona sección...</option>
                    {secciones.map(s => (
                      <option key={s.id} value={s.id}>{s.nombre}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Fecha de Nacimiento</label>
                  <input type="date" name="fecha_nacimiento" value={formData.fecha_nacimiento} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Cargo específico</label>
                  <input type="text" name="cargo" value={formData.cargo} onChange={manejarCambioInput} placeholder="Ej. Seisenero, Subjefe, etc." className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Teléfono de Contacto</label>
                  <input type="text" name="telefono" value={formData.telefono} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
              </div>

              <div className="border-t border-[#e0ece0] pt-3 mt-2 font-semibold text-[#2d6a4f]">👪 Datos de Emergencia y Contacto</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Nombre del Padre o Tutor</label>
                  <input type="text" name="nombre_tutor" value={formData.nombre_tutor} onChange={formData.nombre_tutor} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Teléfono de Emergencia *</label>
                  <input type="text" name="telefono_emergencia" value={formData.telefono_emergencia} onChange={manejarCambioInput} className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Grupo Sanguíneo</label>
                  <input type="text" name="grupo_sanguineo" value={formData.grupo_sanguineo} onChange={manejarCambioInput} placeholder="Ej. O+" className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">Alergias / Padecimientos</label>
                  <input type="text" name="alergias" value={formData.alergias} onChange={manejarCambioInput} placeholder="Ninguna, Polen, etc." className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
                </div>
              </div>

              <div>
                <label className="block font-medium text-gray-700 mb-1">Notas u Observaciones Médicas/Medalla</label>
                <textarea name="notas" value={formData.notas} onChange={manejarCambioInput} rows="2" className="w-full p-2 border border-[#c8dcc8] rounded-lg outline-none focus:border-[#52b788]" />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input type="checkbox" id="activo" name="activo" checked={formData.activo} onChange={manejarCambioInput} className="w-4 h-4 text-[#40916c] border-[#c8dcc8] rounded focus:ring-[#52b788]" />
                <label htmlFor="activo" className="font-medium text-gray-700 select-none">Miembro activo en el escalafón del grupo</label>
              </div>

              <div className="p-4 border-t border-[#e0ece0] flex justify-end gap-3 bg-[#faf8f4] -mx-6 -mb-6 rounded-b-xl">
                <button type="button" onClick={() => setModalAbierto(false)} className="p-2 px-4 bg-white border border-gray-300 rounded-lg text-gray-700 font-semibold hover:bg-gray-50 cursor-pointer">Cancelar</button>
                <button type="submit" className="p-2 px-5 bg-[#40916c] hover:bg-[#2d6a4f] text-white font-bold rounded-lg transition-colors border-none cursor-pointer">💾 Guardar Cambios</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}