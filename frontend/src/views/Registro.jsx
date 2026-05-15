import React, { useState, useEffect } from 'react'

export const Registro = () => {
  const [pagos, setPagos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    fetch('/api/registro/historial', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => r.ok ? r.json() : [])
      .then(data => setPagos(data || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-serif font-bold text-[#1b4332]">Registro Nacional Anual</h2>
        <p className="text-sm text-gray-500 mt-1">Estatus de cuotas de inscripción y vigencia ante la Provincia Aguascalientes.</p>
      </div>

      <div className="bg-white border border-[#c8dcc8] rounded-xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-[#2d6a4f]">Revisando libros contables...</div>
        ) : pagos.length === 0 ? (
          <div className="p-10 text-center text-gray-400 italic">No hay historial de pagos registrado este ciclo.</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-[#f0f5f1] text-[#2d6a4f] text-[11px] font-bold uppercase tracking-wider border-b border-[#c8dcc8]">
              <tr>
                <th className="p-3.5 px-4">Scout</th>
                <th className="p-3.5 px-4">Ciclo Fiscal</th>
                <th className="p-3.5 px-4">Monto Cubierto</th>
                <th className="p-3.5 px-4">Fecha de Pago</th>
                <th className="p-3.5 px-4">Dictamen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e0ece0]">
              {pagos.map((p, idx) => (
                <tr key={idx} className="hover:bg-[#f5fbf6] transition-colors">
                  <td className="p-4 font-bold text-[#0f1e14]">{p.miembro_nombre}</td>
                  <td className="p-4 font-mono text-xs text-gray-500">{p.ano || '2026'}</td>
                  <td className="p-4 font-semibold text-gray-700">${p.monto ? p.monto.toFixed(2) : '350.00'}</td>
                  <td className="p-4 text-xs text-gray-500">{p.fecha_pago || '—'}</td>
                  <td className="p-4">
                    <span className="text-[11px] font-bold bg-[#d8f3dc] text-[#1b4332] px-2.5 py-0.5 rounded-full">
                      {p.estatus || 'Registrado'}
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