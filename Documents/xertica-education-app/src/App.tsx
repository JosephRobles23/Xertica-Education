import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import NuevaRuta from '@/pages/NuevaRuta'
import EstructuraPropuesta from '@/pages/EstructuraPropuesta'
import Ruta from '@/pages/Ruta'
import Storyboard from '@/pages/Storyboard'
import LabGuide from '@/pages/LabGuide'
import AssetFinal from '@/pages/AssetFinal'
import Publicado from '@/pages/Publicado'
import Biblioteca from '@/pages/Biblioteca'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/nueva-ruta" element={<NuevaRuta />} />
        <Route path="/estructura-propuesta" element={<EstructuraPropuesta />} />
        <Route path="/ruta/:id" element={<Ruta />} />
        <Route path="/ruta/:id/video-storyboard" element={<Storyboard />} />
        <Route path="/ruta/:id/lab-guia" element={<LabGuide />} />
        <Route path="/ruta/:id/asset-final" element={<AssetFinal />} />
        <Route path="/ruta/:id/publicado" element={<Publicado />} />
        <Route path="/biblioteca" element={<Biblioteca />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
