import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './auth/AuthContext'
import { LoadingScreen } from './components/States'
import { AppShell } from './layout/AppShell'
import { AuthLayout } from './layout/AuthLayout'

const ActivitiesPage = lazy(() => import('./pages/ActivitiesPage').then((module) => ({ default: module.ActivitiesPage })))
const ActivityAnalysisPage = lazy(() => import('./pages/ActivityAnalysisPage').then((module) => ({ default: module.ActivityAnalysisPage })))
const ActivityDetailPage = lazy(() => import('./pages/ActivityDetailPage').then((module) => ({ default: module.ActivityDetailPage })))
const BootstrapPage = lazy(() => import('./pages/BootstrapPage').then((module) => ({ default: module.BootstrapPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((module) => ({ default: module.ComparePage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((module) => ({ default: module.ProfilePage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage').then((module) => ({ default: module.ResetPasswordPage })))
const StatisticsPage = lazy(() => import('./pages/StatisticsPage').then((module) => ({ default: module.StatisticsPage })))

export function App() {
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
          <Route index element={<DashboardPage />} />
          <Route path="/aktivitaeten" element={<ActivitiesPage />} />
          <Route path="/aktivitaeten/:id/analyse" element={<ActivityAnalysisPage />} />
          <Route path="/aktivitaeten/:id" element={<ActivityDetailPage />} />
          <Route path="/statistiken" element={<StatisticsPage />} />
          <Route path="/vergleich" element={<ComparePage />} />
          <Route path="/coach" element={<ChatPage />} />
          <Route path="/profil" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
