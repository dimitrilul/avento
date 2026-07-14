import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './auth/AuthContext'
import { LoadingScreen } from './components/States'
import { AppShell } from './layout/AppShell'
import { AuthLayout } from './layout/AuthLayout'
import { ClassicContentBoundary, useUiMode } from './UiModeProvider'

const ActivitiesPage = lazy(() => import('./pages/ActivitiesPage').then((module) => ({ default: module.ActivitiesPage })))
const ActivityAnalysisPage = lazy(() => import('./pages/ActivityAnalysisPage').then((module) => ({ default: module.ActivityAnalysisPage })))
const ActivityDetailPage = lazy(() => import('./pages/ActivityDetailPage').then((module) => ({ default: module.ActivityDetailPage })))
const BootstrapPage = lazy(() => import('./pages/BootstrapPage').then((module) => ({ default: module.BootstrapPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((module) => ({ default: module.ComparePage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const MinimalDashboardPage = lazy(() => import('./pages/MinimalDashboardPage').then((module) => ({ default: module.MinimalDashboardPage })))
const DevelopmentPage = lazy(() => import('./pages/DevelopmentPage').then((module) => ({ default: module.DevelopmentPage })))
const GamificationPage = lazy(() => import('./pages/GamificationPage').then((module) => ({ default: module.GamificationPage })))
const MinimalGamificationPage = lazy(() => import('./pages/MinimalGamificationPage').then((module) => ({ default: module.MinimalGamificationPage })))
const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((module) => ({ default: module.ProfilePage })))
const RecordsPage = lazy(() => import('./pages/RecordsPage').then((module) => ({ default: module.RecordsPage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage').then((module) => ({ default: module.ResetPasswordPage })))
const StatisticsPage = lazy(() => import('./pages/StatisticsPage').then((module) => ({ default: module.StatisticsPage })))
const McpAdminPage = lazy(() => import('./pages/McpAdminPage').then((module) => ({ default: module.McpAdminPage })))

export function App() {
  const { minimal } = useUiMode()
  const fallback = (element: React.ReactNode) => minimal ? <ClassicContentBoundary>{element}</ClassicContentBoundary> : element
  return (
    <Suspense fallback={<LoadingScreen label="Avento wird geladen …" />}>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registrieren" element={<RegisterPage />} />
          <Route path="/einrichten" element={<BootstrapPage />} />
          <Route path="/passwort-zuruecksetzen" element={<ResetPasswordPage />} />
        </Route>
        <Route element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={minimal ? <MinimalDashboardPage /> : <DashboardPage />} />
          <Route path="/aktivitaeten" element={fallback(<ActivitiesPage />)} />
          <Route path="/aktivitaeten/:id/analyse" element={fallback(<ActivityAnalysisPage />)} />
          <Route path="/aktivitaeten/:id" element={fallback(<ActivityDetailPage />)} />
          <Route path="/statistiken" element={fallback(<StatisticsPage />)} />
          <Route path="/entwicklung" element={fallback(<DevelopmentPage />)} />
          <Route path="/meilensteine" element={minimal ? <MinimalGamificationPage /> : <GamificationPage />} />
          <Route path="/rekorde" element={fallback(<RecordsPage />)} />
          <Route path="/vergleich" element={fallback(<ComparePage />)} />
          <Route path="/coach" element={fallback(<ChatPage />)} />
          <Route path="/profil" element={fallback(<ProfilePage />)} />
          <Route path="/administration/mcp" element={fallback(<McpAdminPage />)} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
