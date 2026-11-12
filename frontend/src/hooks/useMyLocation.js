import { useState } from 'react'
import { getCoarseLocation } from '../utils/location'

// 버튼을 눌렀을 때만 위치를 묻는다. 받은 위치(약 1km 단위)는 이 탭에서만 기억해
// 홈에 다시 와도 또 누르지 않게 한다 (sessionStorage: 탭을 닫으면 사라지고, 서버로 보내 저장하지 않는다)
const KEY = 'fairpick.nearby'

function load() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(KEY))
    return Number.isFinite(saved?.lat) && Number.isFinite(saved?.lng) ? saved : null
  } catch {
    return null
  }
}

function save(location) {
  try {
    if (location) sessionStorage.setItem(KEY, JSON.stringify(location))
    else sessionStorage.removeItem(KEY)
  } catch {
    // 저장소를 막은 브라우저: 기억하지 못할 뿐 동작은 같다
  }
}

export function useMyLocation({ remember = false } = {}) {
  const [location, setLocation] = useState(() => (remember ? load() : null))
  const [state, setState] = useState({ loading: false, error: '' })

  const locate = async () => {
    setState({ loading: true, error: '' })
    try {
      const next = await getCoarseLocation()
      if (remember) save(next)
      setLocation(next)
      setState({ loading: false, error: '' })
      return next
    } catch (e) {
      setState({ loading: false, error: e.message })
      return null
    }
  }

  const clear = () => {
    if (remember) save(null)
    setLocation(null)
  }

  return { location, locate, clear, ...state }
}
