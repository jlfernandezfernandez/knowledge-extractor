"""The container claims live in, and the rule that names one.

Its own module rather than a fourth model in `claim.py`: that file is about a
claim at each point in its life, and a knowledge base is not a later stage of a
claim, it is the thing a claim is inside. Putting them together would make the
one-sentence answer to "what is claim.py about?" stop being one sentence.

A knowledge base is what a vector store calls a collection (Qdrant, Chroma) or
a namespace (Pinecone); here it is a foreign key plus the leading column of the
indexes that support retrieval. That is exactly why the repository port takes a
`KnowledgeBase` and not a bare id: pgvector wants `id`, a Qdrant adapter would
want `slug` as a collection name, and the port has no business choosing for
them.

`slugify` lives here, with the type it names, rather than next to the HTTP route
that calls it, because a slug is what makes two knowledge bases the same one.
"Kitchen Returns", "kitchen returns" and "Kitchen  Returns!" are one knowledge
base with three spellings of its name, and that collapse has to happen in one
place or they quietly become three.
"""

import re
import unicodedata

from pydantic import BaseModel


class KnowledgeBase(BaseModel):
    id: str
    slug: str  # what a URL, an agent and a unique index use to name it
    name: str
    # Live claims in it. Only the listing pays for the count; resolving a
    # knowledge base to write into it does not need to know how full it is.
    claims: int = 0


def slugify(name: str) -> str:
    """A name reduced to what a URL and a unique index can compare.

    Accents are folded rather than stripped, so "Devoluciones Cocina" and
    "devoluciones cocina" collide instead of becoming two knowledge bases that
    look identical in the sidebar. Standard library only: this is six lines and
    a dependency for it would be six lines plus a dependency.

    Returns "" for a name with nothing usable in it — a name in a script that
    does not transliterate, or one made entirely of punctuation. The caller
    decides what that means; here it is simply not a slug.
    """
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    # Truncated before the final strip, so a cut that lands on a separator does
    # not leave a trailing hyphen behind.
    return re.sub(r"[^a-z0-9]+", "-", folded.lower())[:64].strip("-")
