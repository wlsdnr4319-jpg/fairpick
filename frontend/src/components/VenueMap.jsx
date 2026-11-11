// 오시는 길 (레퍼런스 F-20 지도·길찾기)
// 지도는 OpenStreetMap 퍼가기(iframe)를 쓴다: API 키·라이브러리가 필요 없고, 출처 표기가 지도 안에 들어 있다.
// 길찾기는 카카오맵 링크 (좌표가 있으면 정확한 위치로, 없으면 전시장 이름 검색으로).

const SPAN = { lat: 0.004, lng: 0.006 } // 지도에 보이는 범위 (전시장 주변 약 500m)

export function kakaoMapLinks(venue) {
  const name = encodeURIComponent(venue.name)
  if (venue.latitude == null || venue.longitude == null) {
    return { map: `https://map.kakao.com/link/search/${name}`, route: null }
  }
  const at = `${name},${venue.latitude},${venue.longitude}`
  return { map: `https://map.kakao.com/link/map/${at}`, route: `https://map.kakao.com/link/to/${at}` }
}

export function osmEmbedUrl({ latitude: lat, longitude: lng }) {
  const bbox = [lng - SPAN.lng, lat - SPAN.lat, lng + SPAN.lng, lat + SPAN.lat].map((n) => n.toFixed(6)).join(',')
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lng}`
}

export default function VenueMap({ venue }) {
  const links = kakaoMapLinks(venue)
  const hasLocation = venue.latitude != null && venue.longitude != null
  return (
    <section aria-labelledby="venue-map-title" className="space-y-3">
      <h2 id="venue-map-title" className="font-semibold">오시는 길</h2>
      <div className="text-sm text-gray-700">
        <p className="font-medium">
          {venue.name}
          {venue.hall ? ` ${venue.hall}` : ''}
        </p>
        {venue.address && <p>{venue.address}</p>}
        {venue.parking_note && <p className="text-gray-500">주차: {venue.parking_note}</p>}
      </div>
      {hasLocation && (
        <iframe
          title={`${venue.name} 위치 지도`}
          src={osmEmbedUrl(venue)}
          loading="lazy"
          className="h-56 w-full rounded-xl border sm:h-72"
        />
      )}
      <div className="flex flex-wrap gap-2 text-sm">
        {links.route && (
          <a href={links.route} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-white">
            카카오맵 길찾기
          </a>
        )}
        <a href={links.map} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center rounded-lg border px-4">
          {hasLocation ? '카카오맵에서 보기' : '지도·길찾기'}
        </a>
      </div>
    </section>
  )
}
