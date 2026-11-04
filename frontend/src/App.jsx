import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import AdminDashboard from './pages/admin/AdminDashboard.jsx'
import AdminFairEdit from './pages/admin/AdminFairEdit.jsx'
import AdminFairs from './pages/admin/AdminFairs.jsx'
import AdminReview, { AdminCrawlRuns } from './pages/admin/AdminReview.jsx'
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

// 라우트 목록은 레퍼런스 4장.
// * 라우트는 항상 마지막에 둔다. 없으면 "No routes matched" 경고만 뜨고 빈 화면이 나온다.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/fairs" element={<FairList />} />
        <Route path="/fairs/:fairId" element={<FairDetail />} />
        <Route path="/calendar" element={<Calendar />} />
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
  )
}
