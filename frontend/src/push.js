import { api } from './api/client'

// 브라우저 알림(웹 푸시). 구독은 기기(브라우저)마다 따로다.
// 흐름: 알림 권한 요청 → 서비스 워커 등록 → PushManager.subscribe(서버 공개 키) → 구독 정보를 서버에 저장

export function pushSupported() {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export const fetchPushConfig = () => api.get('/push/config').then((r) => r.data)

// 서버 공개 키(base64url)를 PushManager 가 받는 바이트 배열로 바꾼다
function keyToBytes(base64url) {
  const pad = '='.repeat((4 - (base64url.length % 4)) % 4)
  const raw = atob((base64url + pad).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

async function registration() {
  return navigator.serviceWorker.register('/sw.js')
}

export async function currentSubscription() {
  if (!pushSupported()) return null
  const reg = await navigator.serviceWorker.getRegistration('/sw.js')
  return reg ? reg.pushManager.getSubscription() : null
}

// 권한을 거절하면 Error('denied')
export async function enablePush(publicKey) {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('denied')
  const reg = await registration()
  await navigator.serviceWorker.ready
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyToBytes(publicKey) })
  }
  await api.post('/me/push-subscriptions', sub.toJSON())
  return sub
}

export async function disablePush() {
  const sub = await currentSubscription()
  if (!sub) return
  await api.delete('/me/push-subscriptions', { data: { endpoint: sub.endpoint } })
  await sub.unsubscribe()
}

export const sendTestPush = () => api.post('/me/push-subscriptions/test').then((r) => r.data)
