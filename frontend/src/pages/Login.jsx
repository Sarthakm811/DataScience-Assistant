import { useState } from 'react'

export default function Login({ onAuthenticated }) {
    const apiBase = import.meta.env.VITE_API_URL || ''
    const [mode, setMode] = useState('login')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [submitting, setSubmitting] = useState(false)

    const submit = async (event) => {
        event.preventDefault()
        setSubmitting(true)
        setError(null)
        try {
            const response = await fetch(`${apiBase}/api/auth/${mode}`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            const payload = await response.json().catch(() => ({}))
            if (!response.ok) {
                throw new Error(payload.detail || 'Authentication failed')
            }
            onAuthenticated()
        } catch (requestError) {
            setError(requestError.message)
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
            <form onSubmit={submit} className="card w-full max-w-md space-y-4 p-6">
                <h1 className="text-2xl font-semibold text-slate-900">DataScience Assistant</h1>
                <p className="text-sm text-slate-500">
                    {mode === 'login' ? 'Sign in to continue.' : 'Create an account to continue.'}
                </p>
                <input className="input w-full" required minLength="3" maxLength="128"
                    placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} />
                <input className="input w-full" required minLength="8" maxLength="256"
                    type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} />
                {error && <p className="text-sm text-red-600">{error}</p>}
                <button className="btn-primary w-full" disabled={submitting}>
                    {submitting ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Register'}
                </button>
                <button type="button" className="text-sm text-cyan-700"
                    onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}>
                    {mode === 'login' ? 'Create an account' : 'Already have an account? Sign in'}
                </button>
            </form>
        </main>
    )
}
