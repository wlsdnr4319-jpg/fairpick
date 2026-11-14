import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { deleteFairImage, uploadFairImage } from '../../api/admin'
import { errorMessage } from '../../api/client'
import FairCover from '../../components/FairCover'

const MAX_BYTES = 5 * 1024 * 1024 // 서버 한도와 같다 (UPLOAD_MAX_BYTES)
const ACCEPT = 'image/jpeg,image/png,image/webp'

// 표지 이미지 (박람회 수정 화면). 공식 포스터는 저작권 때문에 올리지 않는다 (11-14 결정):
// 직접 찍은 사진이나 주최 측에 사용 허락을 받은 이미지만. 없으면 예시 사진이나 일러스트 표지를 쓴다.
// 박람회 폼과 따로 바로 저장한다 (폼 안에 두면 <form> 이 겹치고, 저장 버튼 하나에 파일 전송이 섞인다)
export default function CoverImageEditor({ fair }) {
  const qc = useQueryClient()
  const inputId = useId()
  const [file, setFile] = useState(null)
  const [rights, setRights] = useState(false)
  const [message, setMessage] = useState('')

  const done = (saved, text) => {
    qc.setQueryData(['admin', 'fair', String(saved.id)], saved)
    qc.invalidateQueries({ queryKey: ['fairs'] })
    qc.invalidateQueries({ queryKey: ['fair', String(saved.id)] })
    setFile(null)
    setRights(false)
    setMessage(text)
  }
  const upload = useMutation({
    mutationFn: () => uploadFairImage(fair.id, file),
    onSuccess: (saved) => done(saved, '표지 이미지를 바꿨어요'),
    onError: (err) => setMessage(errorMessage(err)),
  })
  const remove = useMutation({
    mutationFn: () => deleteFairImage(fair.id),
    onSuccess: (saved) => done(saved, '이미지를 지우고 기본 표지로 돌아갔어요'),
    onError: (err) => setMessage(errorMessage(err)),
  })
  const busy = upload.isPending || remove.isPending

  const pick = (e) => {
    const chosen = e.target.files?.[0] ?? null
    setMessage('')
    if (chosen && chosen.size > MAX_BYTES) {
      setFile(null)
      e.target.value = ''
      setMessage('이미지는 5MB 이하만 올릴 수 있어요')
      return
    }
    setFile(chosen)
  }

  // FairCover 는 공개 API 모양(category.code)을 쓴다. 관리자 API 는 category 가 코드 문자열이다
  const preview = { id: fair.id, title: fair.title, image_url: fair.image_url, category: { code: fair.category } }

  return (
    <section aria-labelledby={`${inputId}-title`} className="max-w-3xl space-y-3 rounded-xl border p-4">
      <h2 id={`${inputId}-title`} className="font-semibold">
        표지 이미지
      </h2>
      <div className="relative h-36 w-64 max-w-full overflow-hidden rounded-xl bg-gray-100">
        <FairCover fair={preview} />
      </div>
      <p className="text-sm text-gray-600">
        {fair.image_url ? '올린 이미지를 쓰고 있어요.' : '이미지가 없어서 주제가 같은 예시 사진(없으면 일러스트)을 쓰고 있어요.'} 공식 포스터·홍보물은
        저작권이 있어 올리지 않아요.
      </p>

      <div className="space-y-2">
        <label htmlFor={inputId} className="block text-sm text-gray-700">
          새 이미지 (JPG·PNG·WebP, 5MB 이하)
        </label>
        <input
          id={inputId}
          type="file"
          accept={ACCEPT}
          onChange={pick}
          disabled={busy}
          aria-describedby={`${inputId}-hint`}
          className="block text-sm"
        />
        <p id={`${inputId}-hint`} className="text-xs text-gray-500">
          긴 변 1600px 로 줄이고 촬영 위치 같은 사진 정보(EXIF)는 지워서 올려요.
        </p>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} disabled={busy} />
          직접 찍었거나 사용 허락을 받은 이미지예요
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!file || !rights || busy}
          onClick={() => upload.mutate()}
          className="min-h-11 rounded-lg bg-indigo-600 px-4 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {upload.isPending ? '올리는 중…' : '이미지 올리기'}
        </button>
        {fair.image_url && (
          <button
            type="button"
            disabled={busy}
            onClick={() => window.confirm('표지 이미지를 지우고 기본 표지(예시 사진·일러스트)로 돌아갈까요?') && remove.mutate()}
            className="min-h-11 rounded-lg border px-4 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            {remove.isPending ? '지우는 중…' : '이미지 지우기'}
          </button>
        )}
      </div>
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
    </section>
  )
}
