import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { FileScan, Upload, Search } from 'lucide-react'
import ScanPage from './pages/ScanPage'
import UploadPage from './pages/UploadPage'
import QueryPage from './pages/QueryPage'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-2">
                <FileScan className="w-8 h-8 text-indigo-600" />
                <span className="text-xl font-bold text-gray-900">文档扫描管理系统</span>
              </div>
              
              {/* Navigation */}
              <nav className="flex gap-1">
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`
                  }
                >
                  <FileScan className="w-5 h-5" />
                  <span>扫描文档</span>
                </NavLink>
                <NavLink
                  to="/upload"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`
                  }
                >
                  <Upload className="w-5 h-5" />
                  <span>上传文档</span>
                </NavLink>
                <NavLink
                  to="/query"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`
                  }
                >
                  <Search className="w-5 h-5" />
                  <span>结果查询</span>
                </NavLink>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<ScanPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/query" element={<QueryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App