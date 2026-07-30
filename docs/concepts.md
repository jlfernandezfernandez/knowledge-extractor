# Concepts

## Shared knowledge, reviewed by people

Knowli is one shared space of approved claims. A claim is a small statement
that should make sense on its own: for example, “Production deployments happen
on Fridays.” It has an author, source contribution, timestamp, tags, and an
embedding for retrieval.

A model helps turn free-form text into draft claims, but it never publishes one
by itself. The contributor reviews the drafts, then decides how to handle any
meaningful overlap with claims already stored. This is the human-in-the-loop
boundary: models propose and compare; people decide what becomes shared.

## Contributions and review stages

A contribution is the durable record of someone sharing text or answering an
interview. It moves through four stages:

1. **Claims** — the model extracts drafts; the author can edit or remove them.
2. **Conflicts** — likely overlaps are shown for a human decision.
3. **Commit** — validated choices are ready to persist.
4. **Committed** — approved claims are available to Ask and History.

Every change carries a revision number. The server rejects a stale revision,
which prevents two browser tabs from silently overwriting each other’s review.

## Overlap and lineage

Similarity is not automatically a contradiction. The comparison model can mark
two claims as a conflict, duplicate, refinement, or unrelated. For a relevant
pair, the contributor may keep the new claim, keep the existing one, keep both,
or merge them into a replacement statement.

When a newer statement replaces an older one, the old record receives a
`superseded_by` link. It remains in the database for history while normal
retrieval filters it out. That preserves a useful answer to “what changed?”
without returning obsolete advice as current fact.

## Embeddings, full-text search, and RRF

An embedding is a list of numbers representing the meaning of text. Similar
meanings tend to be near each other, so vector search is useful for paraphrases.
It is not enough by itself: exact identifiers, acronyms, and version numbers
often matter too.

Knowli also uses PostgreSQL full-text search. The store takes the top candidates
from both methods and combines their ranks with reciprocal rank fusion (RRF): a
small score is added for a high position in either list. A claim appearing near
the top in both lists naturally rises; a strong exact match or semantic match
can still be found when the other method misses it.

## Cited answers

Ask first retrieves only committed, current claims. The model receives that
small evidence set and returns an answer plus the IDs it relies on. Knowli
intersects those IDs with the retrieved set before returning citations, so the
interface cannot cite an unseen claim. If retrieval produces no evidence, Ask
returns an explicit insufficient-evidence response rather than inventing one.

## Interviews

An interview is a direct request from one registered user to another. Only the
assignee can start and answer it; both people can view the resulting interview
through the linked contribution. The answer follows the same review graph as a
voluntary contribution, so it cannot bypass human approval.

## Authentication and authorship

Registration stores a password hash, not a password. Successful login creates
a random session token; the server stores only its hash and sends the original
token in an HTTP-only, same-site cookie. Each contribution records its author,
and contribution review is author-only. Reading the shared space requires a
signed-in account.
