import React, { useState } from 'react'

const Login = ({ onLoginSuccess, onCancel }) => { // ← Aquí agregamos onCancel
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Ingresa tu correo y contraseña.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password })
      })
      
      const data = await res.json()
      
      if (!res.ok) throw new Error(data.detail || 'Credenciales inválidas.')

      sessionStorage.setItem('scout_token', data.token)
      onLoginSuccess(data.usuario)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[9999] bg-[#1b4332] flex items-center justify-center p-4">
      <div className="bg-white rounded-[20px] p-10 md:px-9 md:py-8 w-full max-w-[360px] text-center relative shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
        
        {/* Tachita de cerrar - Ahora es un botón de React */}
        <button 
          onClick={onCancel} 
          className="absolute top-3 right-3 w-7 h-7 rounded-full flex items-center justify-center text-[#8aab92] hover:bg-[#f0f5f1] hover:text-[#1a2e1e] transition-colors text-base border-none bg-transparent cursor-pointer"
        >
          ✕
        </button>
        
        <div className="text-4xl mb-3.5">⚜️</div>
        <h2 className="font-serif text-2xl font-semibold text-[#1b4332] mb-1">ScoutDB Intranet</h2>
        <p className="text-xs text-[#8aab92] mb-6">Sistema de gestión · Grupo Scout 22</p>

        <form onSubmit={handleLogin} className="space-y-3">
          <input 
            type="text" 
            className="w-full p-3.5 bg-white border border-[#c8dcc8] rounded-lg focus:border-[#52b788] outline-none transition-all text-base"
            placeholder="correo@tudominio.org"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
          
          <input 
            type="password" 
            className="w-full p-3.5 bg-white border border-[#c8dcc8] rounded-lg focus:border-[#52b788] outline-none transition-all text-base"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />

          <button 
            type="submit" 
            className="w-full p-3.5 bg-[#1b4332] text-white rounded-lg font-bold text-sm hover:bg-[#2d6a4f] transition-colors cursor-pointer disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Verificando...' : 'Entrar →'}
          </button>
        </form>

        {/* Botón de volver - Ahora es un botón de React */}
        <button 
          onClick={onCancel} 
          className="block mt-4 text-xs text-[#8aab92] hover:text-[#2d6a4f] transition-colors no-underline mx-auto bg-transparent border-none cursor-pointer font-sans"
        >
          ← Volver a la página principal
        </button>

        {error && (
          <div className="text-xs text-[#c0392b] mt-3 min-h-4 font-semibold">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}

export default Login