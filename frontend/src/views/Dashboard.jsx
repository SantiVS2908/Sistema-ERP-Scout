import React, { useState, useEffect } from 'react'

export const Dashboard = ({ user }) => {
  const [stats, setStats] = useState({
    total_miembros: 0,
    total_secciones: 0,
    registrados_anio: 0,
    pendientes_registro: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    
    fetch('/api/dashboard', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.ok ? r.json() : {})
      .then(data => {
        // Sintonizamos los nombres exactos que vienen de tu main.py
        setStats({
          total_miembros: data.total_miembros || 0,
          total_secciones: data.total_secciones || 0,
          registrados_anio: data.registrados_anio || 0,
          pendientes_registro: data.pendientes_registro || 0
        })
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-serif font-bold text-[#1b4332]">¡Bienvenido de vuelta, {user?.nombre_completo || 'Scouter'}!</h2>
        <p className="text-sm text-gray-500 mt-1">Aquí está el resumen del estado de fuerza del Grupo Scout 22 Quetzalcóatl.</p>
      </div>

      {/* METRIC CARDS SINCRONIZADAS CON TU POSTGRES */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 border border-[#c8dcc8] rounded-xl shadow-xs">
          <div className="text-xs font-bold uppercase tracking-wider text-[#2d6a4f]">⚜️ Membresía Total</div>
          <div className="text-3xl font-serif font-black text-[#1b4332] mt-2">
            {loading ? '...' : `${stats.total_miembros} Scouts`}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Activos en el sistema</div>
        </div>

        <div className="bg-white p-5 border border-[#c8dcc8] rounded-xl shadow-xs">
          <div className="text-xs font-bold uppercase tracking-wider text-[#457b9d]">⛺ Secciones</div>
          <div className="text-3xl font-serif font-black text-[#1b4332] mt-2">
            {loading ? '...' : `${stats.total_secciones} Ramas`}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Vivas en el grupo</div>
        </div>

        <div className="bg-white p-5 border border-[#c8dcc8] rounded-xl shadow-xs">
          <div className="text-xs font-bold uppercase tracking-wider text-[#e8a217]">💰 Registro Nacional</div>
          <div className="text-3xl font-serif font-black text-[#1b4332] mt-2">
            {loading ? '...' : `${stats.registrados_anio} Listos`}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Inscripción avalada este ciclo</div>
        </div>

        <div className="bg-white p-5 border border-[#c8dcc8] rounded-xl shadow-xs">
          <div className="text-xs font-bold uppercase tracking-wider text-red-700">⏳ Trámites Pendientes</div>
          <div className="text-3xl font-serif font-black text-red-900 mt-2">
            {loading ? '...' : `${stats.pendientes_registro} Faltan`}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Requieren atención de jefatura</div>
        </div>
      </div>

      {/* AVISOS DE COMANDANCIA */}
      <div className="bg-[#f5ede4] p-5 border border-[#8b5e3c]/20 rounded-xl">
        <h3 className="font-serif font-bold text-[#8b5e3c] mb-1">📢 Recordatorio de Jefatura</h3>
        <p className="text-xs text-[#8b5e3c]/80 leading-relaxed">
          Es obligatorio que todos los scouters verifiquen que sus muchachos cuenten con el registro anual vigente antes del campamento de verano. Las altas nuevas hechas desde este panel actualizan Postgres en tiempo real.
        </p>
      </div>
    </div>
  )
}