import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import NotFound from './pages/NotFound.jsx'

// 라우트 목록은 레퍼런스 4장. 화면은 주차별로 추가한다.
//   2~3주차: /fairs, /fairs/:fairId
//   4주차:   /login, /signup, /mypage, /mypage/settings
//   5주차:   /admin, /admin/fairs, /admin/fairs/:fairId/edit
//   6주차:   /admin/review
// * 라우트는 항상 마지막에 둔다. 없으면 "No routes matched" 경고만 뜨고 빈 화면이 나온다.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
