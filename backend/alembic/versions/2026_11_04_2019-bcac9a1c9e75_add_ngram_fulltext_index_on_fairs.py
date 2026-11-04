"""add ngram fulltext index on fairs

Revision ID: bcac9a1c9e75
Revises: d00165b60df6
Create Date: 2026-11-04 20:19:34.614545

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcac9a1c9e75"
down_revision: str | Sequence[str] | None = "d00165b60df6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """한글 키워드 검색: 앞에 %가 붙은 LIKE 는 인덱스를 못 써서 ngram FULLTEXT 로 바꾼다 (레퍼런스 6장, 11주차)."""
    op.execute("ALTER TABLE fairs ADD FULLTEXT INDEX ft_fairs (title, summary) WITH PARSER ngram")


def downgrade() -> None:
    op.execute("ALTER TABLE fairs DROP INDEX ft_fairs")
