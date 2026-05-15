import React, { useState, useEffect } from 'react'

export const Uniformes = () => {
  const [inventario, setInventario] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    fetch('/api/uniformes/resumen', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.ok ? r.json() : [])
      .then(data => setInventario(data || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-serif font-bold text-[#1b4332]">Control de Uniformes</h2>
        <p className="text-sm text-gray-500 mt-1">Monitoreo de equipo, parches y estado del uniforme de los miembros.</p>
      </div>

      <div className="bg-white border border-[#c8dcc8] rounded-xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-[#2d6a4f]">Consultando almacén textil...</div>
        ) : inventario.length === 0 ? (
          <div className="p-10 text-center text-gray-400 italic">No hay registros de uniformes capturados.</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-[#f0f5f1] text-[#2d6a4f] text-[11px] font-bold uppercase tracking-wider border-b border-[#c8dcc8]">
              <tr>
                <th className="p-3.5 px-4">Miembro</th>
                <th className="p-3.5 px-4">Pieza de Uniforme</th>
                <th className="p-3.5 px-4">Talla</th>
                <th className="p-3.5 px-4">Estado de Entrega</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e0ece0]">
              {inventario.map((item, idx) => (
                <tr key={idx} className="hover:bg-[#f5fbf6] transition-colors">
                  <td className="p-4 font-bold text-[#0f1e14]">{item.miembro_nombre}</td>
                  <td className="p-4 text-gray-600">{item.pieza}</td>
                  <td className="p-4 font-mono text-xs">{item.talla || 'M'}</td>
                  <td className="p-4">
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${item.status === 'Completo' ? 'bg-[#d8f3dc] text-[#1b4332]' : 'bg-amber-100 text-amber-700'}`}>
                      {item.status || 'Entregado'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}