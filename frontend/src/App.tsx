import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/app/providers/AuthProvider'
import { AppRoutes } from '@/app/routes/AppRoutes'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
