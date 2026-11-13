import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Loading } from './components/ui'

// Each page is its own chunk, so the first load only pulls in what it shows.
const Overview = lazy(() => import('./pages/Overview'))
const Segments = lazy(() => import('./pages/Segments'))
const Targeting = lazy(() => import('./pages/Targeting'))
const Score = lazy(() => import('./pages/Score'))
const Insights = lazy(() => import('./pages/Insights'))

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/segments" element={<Segments />} />
          <Route path="/targeting" element={<Targeting />} />
          <Route path="/score" element={<Score />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="*" element={<Overview />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
