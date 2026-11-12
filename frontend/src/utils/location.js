// '내 주변 박람회'용 현재 위치. 위치는 서버에 저장하지 않고 검색 주소(URL)에만 쓴다.
// 소수 둘째 자리(위도 약 1.1km)로 줄여 보내서, 주소를 공유하거나 접속 기록에 남아도 정확한 위치는 드러나지 않는다.
export const roundCoord = (n) => Math.round(n * 100) / 100

export function getCoarseLocation() {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('이 브라우저는 위치 기능을 지원하지 않아요.'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: roundCoord(pos.coords.latitude), lng: roundCoord(pos.coords.longitude) }),
      (err) =>
        reject(
          new Error(
            err.code === err.PERMISSION_DENIED
              ? '위치 권한이 꺼져 있어요. 브라우저 주소창의 사이트 설정에서 위치를 허용해 주세요.'
              : '위치를 가져오지 못했어요. 잠시 후 다시 시도해 주세요.',
          ),
        ),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 10 * 60_000 },
    )
  })
}
