"""
분석 노트북(fairs_report.ipynb)을 만들고 실행해 결과(표·차트)까지 저장한다.
GitHub 에서 노트북을 열면 실행 결과가 그대로 보인다 (레퍼런스 12장 산출물).

    cd analysis
    py -3.13 -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt
    .venv\\Scripts\\python build_notebook.py

DB 주소는 저장소 루트의 .env 에 있는 DATABASE_URL 을 쓴다.
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).parent

cells = [
    nbformat.v4.new_markdown_cell(
        "# 페어픽 박람회 데이터 분석\n\n"
        "'언제, 어디서, 어떤 박람회가 많이 열리는가'를 페어픽에 모인 데이터로 살펴본다.\n"
        "공개·숨김(지난 행사) 박람회를 함께 세고, 검수 전 초안은 뺀다. 데이터가 쌓일수록 다시 실행해 갱신한다."
    ),
    nbformat.v4.new_code_cell(
        """import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

# matplotlib 기본 폰트에는 한글이 없어 글자가 네모로 깨진다 (레퍼런스 17장 트러블슈팅)
plt.rcParams["font.family"] = "Malgun Gothic"  # macOS/Linux 는 "AppleGothic" / "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False
for side in ("top", "right"):
    plt.rcParams[f"axes.spines.{side}"] = False

def database_url():
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    for line in (Path.cwd().parent / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1]
    raise RuntimeError("DATABASE_URL 이 없어요")

engine = create_engine(database_url())
df = pd.read_sql(
    "SELECT f.id, f.title, f.start_date, f.end_date, f.price_onsite, f.price_prereg, f.public_access, "
    "       c.code AS category_code, c.name AS category, v.name AS venue, v.region "
    "FROM fairs f JOIN categories c ON c.id = f.category_id JOIN venues v ON v.id = f.venue_id "
    "WHERE f.status IN ('published', 'hidden')",
    engine,
    parse_dates=["start_date", "end_date"],
)
df["month"] = df["start_date"].dt.to_period("M")
df["days"] = (df["end_date"] - df["start_date"]).dt.days + 1
df["free"] = (df["price_onsite"] == 0) | (df["price_prereg"] == 0)
# 맑은 고딕에는 가운뎃점(·) 글자가 없어 빈칸으로 보인다. 한글 가운뎃점(ㆍ)으로 바꿔 표시한다
df["category"] = df["category"].str.replace("·", "ㆍ")
print(f"박람회 {len(df)}개, 기간 {df['start_date'].min():%Y-%m-%d} ~ {df['end_date'].max():%Y-%m-%d}")"""
    ),
    nbformat.v4.new_markdown_cell("## 1. 월별로 언제 많이 열리나\n\n카테고리 색은 서비스의 통계 화면과 같다 (카테고리마다 고정)."),
    nbformat.v4.new_code_cell(
        """COLORS = {"식음료": "#2a78d6", "문화ㆍ예술": "#eb6834", "라이프스타일": "#1baf7a", "취미ㆍ레저": "#eda100",
          "반려동물": "#e87ba4", "가족ㆍ육아": "#008300", "테크ㆍ게임": "#6250d6"}
monthly = df.pivot_table(index="month", columns="category", values="id", aggfunc="count", fill_value=0)
# 박람회가 없는 달도 0 으로 보여 달 간격을 고르게 한다
monthly = monthly.reindex(pd.period_range(monthly.index.min(), monthly.index.max(), freq="M"), fill_value=0)
monthly = monthly[[c for c in COLORS if c in monthly.columns]]
monthly.index = [f"{p.year}.{p.month}" for p in monthly.index]  # 막대 축 라벨: 2026.4
ax = monthly.plot(kind="bar", stacked=True, figsize=(10, 4), width=0.7, edgecolor="white", linewidth=1.5,
                  color=[COLORS[c] for c in monthly.columns])
ax.set_title("월별 박람회 수", loc="left")
ax.set_xlabel(""); ax.set_ylabel("박람회 수")
ax.tick_params(axis="x", rotation=0)
ax.legend(frameon=False, ncols=4, fontsize=9, loc="upper left")
ax.grid(axis="y", color="#e1e0d9"); ax.set_axisbelow(True)
plt.tight_layout(); plt.show()
monthly.assign(합계=monthly.sum(axis=1))"""
    ),
    nbformat.v4.new_markdown_cell("## 2. 카테고리별 비중, 평균 기간, 무료 비율"),
    nbformat.v4.new_code_cell(
        """by_cat = (
    df.groupby("category")
    .agg(개최수=("id", "count"), 평균기간_일=("days", "mean"), 무료비율=("free", "mean"))
    .sort_values("개최수", ascending=False)
)
by_cat["비중"] = by_cat["개최수"] / by_cat["개최수"].sum()

fig, ax = plt.subplots(figsize=(8, 3.5))
ax.barh(by_cat.index[::-1], by_cat["개최수"][::-1], color="#2a78d6", height=0.55)
for y, v in enumerate(by_cat["개최수"][::-1]):
    ax.text(v + 0.1, y, str(v), va="center", fontsize=9, color="#52514e")
ax.set_title("카테고리별 개최 수", loc="left"); ax.set_xticks([])
plt.tight_layout(); plt.show()
by_cat.style.format({"평균기간_일": "{:.1f}", "무료비율": "{:.0%}", "비중": "{:.0%}"})"""
    ),
    nbformat.v4.new_markdown_cell("## 3. 전시장별로 어떤 박람회가 많이 열리나"),
    nbformat.v4.new_code_cell(
        """by_venue = pd.crosstab(df["venue"], df["category"])
by_venue["합계"] = by_venue.sum(axis=1)
by_venue["가장 많은 카테고리"] = by_venue.drop(columns="합계").idxmax(axis=1)
by_venue.sort_values("합계", ascending=False)"""
    ),
    nbformat.v4.new_markdown_cell("## 4. 무료로 갈 수 있는 박람회는 몇 %인가"),
    nbformat.v4.new_code_cell(
        """known = df[df["price_onsite"].notna() | df["price_prereg"].notna()]
print(f"전체 {len(df)}개 중 무료(현장 또는 사전등록) {df['free'].sum()}개 = {df['free'].mean():.0%}")
print(f"입장료 정보가 있는 {len(known)}개 기준: 무료 {known['free'].mean():.0%}")
print("입장료를 모르는 박람회가 많을수록 이 비율은 낮게 나온다. 검수 때 입장료를 채우면 정확해진다.")"""
    ),
    nbformat.v4.new_markdown_cell(
        "## 정리\n\n"
        "- 데이터는 수집 워커가 매일 쌓는다. 1단계를 일찍 배포할수록 분석할 거리가 많아진다.\n"
        "- 지난 행사 목록을 한 번 수집해 `status='hidden'` 으로 넣으면, 서비스에는 안 보이고 계절별 추이 분석에만 쓸 수 있다."
    ),
]

nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
nbformat.write(nb, HERE / "fairs_report.ipynb")
print("written:", HERE / "fairs_report.ipynb")
