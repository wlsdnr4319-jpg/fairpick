import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="py-16 text-center">
      <p className="text-5xl font-bold text-gray-300">404</p>
      <h1 className="mt-4 text-xl font-semibold">페이지를 찾을 수 없어요</h1>
      <Link
        to="/"
        className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-indigo-600 hover:bg-indigo-700 px-5 text-white hover:bg-indigo-700"
      >
        홈으로 가기
      </Link>
    </section>
  )
}
