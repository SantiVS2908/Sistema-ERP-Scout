import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import { Landing } from './views/Landing' 
import { Biblioteca } from './views/Biblioteca'
import { Miembros } from './views/Miembros'
import { Dashboard } from './views/Dashboard' 
import { Uniformes } from './views/Uniformes'   
import { Registro } from './views/Registro'   

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('landing') // ← 'landing' | 'login' | 'intranet'
  const [currentPage, setCurrentPage] = useState('dashboard') // Controla el menú interno de la intranet

  // Validador de sesión
  useEffect(() => {
    const token = sessionStorage.getItem('scout_token')
    if (!token) {
      setLoading(false)
      return
    }

    fetch('/api/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
      .then(r => {
        if (r.ok) return r.json()
        throw new Error('token_invalido')
      })
      .then(userData => {
        setUser(userData)
        setView('intranet') 
      })
      .catch(() => {
        sessionStorage.removeItem('scout_token')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const handleLogout = () => {
    sessionStorage.removeItem('scout_token')
    setUser(null)
    setView('landing') 
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f0f5f1] flex items-center justify-center text-[#1b4332] font-bold text-lg">
        ⚜️ Cargando sistema ScoutDB...
      </div>
    )
  }

  // ─── RENDERS CONDICIONALES DE TUS VISTAS PÚBLICAS ───
  if (view === 'landing') return <Landing onNavigate={(dest) => setView(dest)} />
  if (view === 'login') return <Login onLoginSuccess={(u) => { setUser(u); setView('intranet') }} onCancel={() => setView('landing')} />
  if (view === 'biblioteca') return <Biblioteca onNavigate={(dest) => setView(dest)} />

  // ─── RENDERS DE LA INTRANET PRIVADA ───
  return (
    <div className="h-screen w-screen bg-[#f0f5f1] text-[#1a2e1e] flex overflow-hidden text-sm font-sans selection:bg-[#d8f3dc]">
      
      {/* SIDEBAR NAVEGACIÓN */}
      <aside className="w-[230px] min-w-[230px] bg-[#1b4332] flex flex-col overflow-hidden text-white">
        <div className="p-[22px_20px_18px] border-b border-white/10">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-8 h-8 bg-[#52b788] rounded-lg flex items-center justify-center text-lg">⚜️</div>
            <span className="font-serif text-lg tracking-wide font-bold">ScoutDB</span>
          </div>
          <div className="text-[11px] text-white/45 ml-11">Sistema de gestión scout</div>
        </div>

        {/* Perfil de Usuario Activo */}
        <div className="p-3 px-4 border-b border-white/10 bg-black/10">
          <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Sesión</div>
          <div className="font-semibold truncate text-white">{user?.nombre_completo}</div>
          <div className="text-[11px] text-white/50 capitalize mt-0.5">{user?.rol}</div>
        </div>

        {/* Menú de Navegación Interna */}
        <nav className="flex-1 overflow-y-auto py-3">
          <div className="px-5 pt-3.5 pb-1 text-[10px] font-bold text-white/30 tracking-[1.5px] uppercase">Principal</div>
          
          <button 
            onClick={() => setCurrentPage('dashboard')}
            className={`w-full text-left px-5 py-2 flex items-center gap-2.5 transition-colors font-medium border-l-3 ${currentPage === 'dashboard' ? 'bg-[#52b788]/15 border-[#52b788] text-white' : 'border-transparent text-white/60 hover:bg-white/5 hover:text-white'}`}
          >
            <span>🏠</span> Inicio
          </button>
          
          <button 
            onClick={() => setCurrentPage('miembros')}
            className={`w-full text-left px-5 py-2 flex items-center gap-2.5 transition-colors font-medium border-l-3 ${currentPage === 'miembros' ? 'bg-[#52b788]/15 border-[#52b788] text-white' : 'border-transparent text-white/60 hover:bg-white/5 hover:text-white'}`}
          >
            <span>👤</span> Miembros
          </button>

          <button 
            onClick={() => setCurrentPage('uniformes')}
            className={`w-full text-left px-5 py-2 flex items-center gap-2.5 transition-colors font-medium border-l-3 ${currentPage === 'uniformes' ? 'bg-[#52b788]/15 border-[#52b788] text-white' : 'border-transparent text-white/60 hover:bg-white/5 hover:text-white'}`}
          >
            <span>👕</span> Uniformes
          </button>

          <button 
            onClick={() => setCurrentPage('registro')}
            className={`w-full text-left px-5 py-2 flex items-center gap-2.5 transition-colors font-medium border-l-3 ${currentPage === 'registro' ? 'bg-[#52b788]/15 border-[#52b788] text-white' : 'border-transparent text-white/60 hover:bg-white/5 hover:text-white'}`}
          >
            <span>💰</span> Registro Anual
          </button>
        </nav>

        <div className="p-3 px-4 border-t border-white/10">
          <button 
            onClick={handleLogout}
            className="w-full p-2 bg-red-900/15 border border-red-900/30 text-red-200 rounded-md text-xs cursor-pointer hover:bg-red-900/30 hover:text-white transition-all font-semibold"
          >
            ← Cerrar sesión
          </button>
        </div>
      </aside>

      {/* ÁREA DE CONTENIDO PRINCIPAL */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="h-14 bg-white border-b border-[#c8dcc8] flex items-center px-6 gap-3.5 shadow-[0_1px_4px_rgba(27,67,50,0.06)] shrink-0">
          <h1 className="font-serif text-xl font-bold text-[#1b4332] capitalize">{currentPage === 'dashboard' ? 'Inicio' : currentPage}</h1>
        </header>

        {/* CONTENIDO VARIABLE */}
        <div className="flex-1 overflow-auto p-6 bg-[#faf8f4]">
          {currentPage === 'dashboard' && (
            <Dashboard user={user} />
          )}

          {currentPage === 'miembros' && (
            <Miembros user={user} />
          )}

          {currentPage === 'uniformes' && (
            <Uniformes />
          )}

          {currentPage === 'registro' && (
            <Registro />
          )}
        </div>
      </main>
    </div>
  )
}

export default App