import { Outlet } from 'react-router-dom'

function App() {
    return (
        <div className="app">
            <header>
                <h1>PostGISで最寄りの世界遺産を検索</h1>
            </header>
            <main>
                <Outlet />
            </main>
        </div>
    )
}

export default App 