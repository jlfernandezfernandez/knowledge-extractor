# Agent protocols: what to use, what to know about

The 2026 landscape, and where this project sits in it.

---

## The one distinction that matters

**MCP is vertical. A2A is horizontal.** They are not competitors; a serious
system speaks both.

```
                  ┌─────────────────────┐
   another team's │   Their agent       │
   autonomous     └──────────┬──────────┘
   agent                     │  A2A  (peer ↔ peer: discover, delegate, negotiate)
                  ┌──────────▼──────────┐
                  │       Knowli        │
                  └──────────┬──────────┘
                             │  MCP  (model ↔ tools & data: "here is a capability")
                  ┌──────────▼──────────┐
                  │ Postgres, retrieval │
                  └─────────────────────┘
```

- **MCP** (Model Context Protocol, Anthropic, Nov 2024) connects *one model* to
  tools and data. If you have ever configured a server in Claude Desktop or
  Cursor, that is MCP. It is the "USB-C port for LLM tools" analogy.
- **A2A** (Agent2Agent, Google, April 2025) connects *agents to each other* as
  peers. Agents publish an **Agent Card** describing their skills, then exchange
  **Tasks** and **Messages** over JSON-RPC/HTTP. It reached **v1.0 in April
  2026**, is governed by the **Linux Foundation**, and has 150+ supporting
  organisations.

> **Say it like this:** "MCP gives a model a tool. A2A lets two autonomous
> agents, built by different teams and different vendors, work together. This
> project exposes both because a coding assistant and another team's agent want
> different things from it."

---

## What this project exposes

Both surfaces enforce the same rule: **an agent may read freely, but may not
write.** `submit_knowledge` returns a review URL. A human still has to confirm
and resolve. The gate is the product; it does not get an exemption for machine
callers.

| Skill / tool | Reads | Writes | Where |
|---|---|---|---|
| `list_knowledge_bases` | the knowledge bases here, with claim counts | — | both |
| `search_knowledge` | hybrid retrieval over live claims | — | both |
| `ask_knowledge` | cited answer grounded in claims | — | both |
| `claim_history` | the supersede chain of a claim | — | MCP only |
| `submit_knowledge` | — | **no** — opens a human review, returns its URL | both |

`claim_history` is MCP-only on purpose. Following a supersede chain is what a
model does mid-task when an answer looks stale — the vertical link. A peer agent
consulting this knowledge base wants the current answer, not our revision
history, so it is not on the Agent Card.

**Every skill that touches claims takes an optional knowledge base**, as a slug,
defaulting to the configured one. That is why `list_knowledge_bases` is there at
all: a peer should be able to name a scope instead of guessing at it. An unknown
slug is an error whose message lists the ones that exist — never a silent
fallback to the default, which would let an agent file a claim into the wrong
subject and then have it compared against that subject's claims. A2A carries it
in the message `metadata` alongside the skill; MCP takes it as a tool argument;
`claim_history` takes none, because a claim id already names its scope.

### MCP

```bash
cd backend && uv pip install -e '.[mcp]'
```

```json
{ "mcpServers": { "knowli": { "command": "knowli-mcp" } } }
```

Runs over stdio, so any MCP client picks it up. This is the realistic
integration path for "our company chat assistant should know our internal
processes".

### A2A

```bash
cd backend && uv pip install -e '.[a2a]' && knowli-a2a
# agent card: http://127.0.0.1:9999/.well-known/agent-card.json
```

Two things that cost real debugging time and are not obvious from the docs:

- The JSON-RPC method is **`SendMessage`** (not `message/send`).
- The **`A2A-Version: 1.0` header is required**. Without it the server assumes
  protocol 0.3 and rejects the call with `-32009`.

```bash
curl -s -X POST localhost:9999/ \
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{
       "message":{"messageId":"u1","role":"ROLE_USER",
                  "parts":[{"text":"when do we deploy?"}]},
       "metadata":{"skill":"ask_knowledge","knowledge_base":"kitchen-returns"}}}'
```

Skill selection rides on message `metadata`, and so does the knowledge base; the
defaults are search and the configured knowledge base.

---

## The rest of the landscape, briefly

Worth being able to name, not worth building on here.

| Protocol | Who | What | Relevant here? |
|---|---|---|---|
| **MCP** | Anthropic | model ↔ tools/data | **yes, implemented** |
| **A2A** | Google → Linux Foundation | agent ↔ agent | **yes, implemented** |
| **AP2** | Google | Agent Payments — mandates for agents transacting on your behalf | no, nothing is bought |
| **A2UI** | A2A extension | agent-driven UI | interesting later — an agent could render its own review widget |
| **UCP** | A2A extension | universal commerce | no |
| **ACP** | IBM | agent communication | overlaps A2A; A2A won the mindshare |
| **ANP** | community | agent network / discovery | no |

The composition story the ecosystem tells: *an MCP-equipped shopping agent uses
A2A to negotiate with a merchant agent, then AP2 to settle.* Three layers, one
stack.

### Agent Skills (`SKILL.md`)

Not a wire protocol — a **packaging format**. A folder with a `SKILL.md`: YAML
frontmatter (`name`, `description`, `version`) plus a Markdown body of
instructions, optionally with `scripts/`, `references/` and `assets/`. The agent
sees only the ~100-token description until the task calls for the skill, then
loads the body. That is **progressive disclosure**, and it is the same idea as
retrieval: keep the context window for what is relevant right now.

Standardised at [agentskills.io](https://agentskills.io), supported by
Anthropic, OpenAI and Microsoft. (This is what the user meant by "frontmatter
for markdown" — it is Agent Skills, and it is an open standard rather than a
Google one.)

**Where it fits this project, and a good next issue:** ship a `SKILL.md` that
teaches an agent *how to interview a person well* — the questions that get tacit
knowledge out of someone — and let the extraction step load it. The prompt
becomes a versioned artifact instead of a constant in
`infrastructure/llm/prompts.py`.

### `llms.txt`

A convention, not a standard: a Markdown file at your domain root listing your
documentation so agents can find it without scraping HTML. Cheap to add to the
docs site; ignore until there is a docs site.

---

## Sources

- [A2A one-year retrospective, Google Open Source Blog, April 2026](https://opensource.googleblog.com/2026/04/a-year-of-open-collaboration-celebrating-the-anniversary-of-a2a.html)
- [Linux Foundation: A2A passes 150 organisations](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
- [Announcing AP2, Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol)
- [Agent Skills specification](https://agentskills.io/specification)
- [Security threat modelling for MCP, A2A, Agora and ANP (arXiv)](https://arxiv.org/pdf/2602.11327)
