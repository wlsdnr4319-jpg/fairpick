import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { MyVisits, ResetPassword, Unsubscribe } from './pages/Account.jsx'
import Calendar from './pages/Calendar.jsx'
import FairDetail from './pages/FairDetail.jsx'
import FairList from './pages/FairList.jsx'
import Home from './pages/Home.jsx'
import { Privacy, Terms } from './pages/Legal.jsx'
import Login from './pages/Login.jsx'
import MyPage, { Settings } from './pages/MyPage.jsx'
import NotFound from './pages/NotFound.jsx'
import Signup from './pages/Signup.jsx'
import { AdminRoute, GuestOnlyRoute, ProtectedRoute } from './routes/Guards.jsx'

// 통계(차트 라이브러리)와 관리자 화면은 처음 열 때 따로 받는다. 일반 방문자의 첫 로딩을 가볍게 한다
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard.jsx'))
const AdminFairEdit = lazy(() => import('./pages/admin/AdminFairEdit.jsx'))
const AdminFairs = lazy(() => import('./pages/admin/AdminFairs.jsx'))
const AdminReview = lazy(() => import('./pages/admin/AdminReview.jsx'))
const AdminCrawlRuns = lazy(() => import('./pages/admin/AdminReview.jsx').then((m) => ({ default: m.AdminCrawlRuns })))
const Report = lazy(() => import('./pages/Report.jsx'))

// 라우트 목록은 레퍼런스 4장.
// * 라우트는 항상 마지막에 둔다. 없으면 "No routes matched" 경고만 뜨고 빈 화면이 나온다.
export default function App() {
  return (
    <Suspense fallback={<p className="py-16 text-center text-gray-400">불러오는 중…</p>}>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/fairs" element={<FairList />} />
        <Route path="/fairs/:fairId" element={<FairDetail />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/report" element={<Report />} />
        <Route path="/unsubscribe" element={<Unsubscribe />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />

        <Route element={<GuestOnlyRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/reset-password" element={<ResetPassword />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/mypage" element={<MyPage />} />
          <Route path="/mypage/settings" element={<Settings />} />
          <Route path="/mypage/visits" element={<MyVisits />} />
        </Route>

        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/fairs" element={<AdminFairs />} />
          <Route path="/admin/fairs/new" element={<AdminFairEdit />} />
          <Route path="/admin/fairs/:fairId/edit" element={<AdminFairEdit />} />
          <Route path="/admin/review" element={<AdminReview />} />
          <Route path="/admin/crawl-runs" element={<AdminCrawlRuns />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  )
}
