import { NextRequest, NextResponse } from 'next/server'

const REPO  = 'JubroPark/ma3-momentum'
const PATH  = 'app/public/data/push_subscriptions.json'
const BRANCH = 'main'
const API   = `https://api.github.com/repos/${REPO}/contents/${PATH}`

async function ghHeaders() {
  return {
    Authorization: `Bearer ${process.env.GH_PAT}`,
    Accept: 'application/vnd.github+json',
    'Content-Type': 'application/json',
  }
}

async function readSubs(): Promise<{ subs: object[]; sha: string }> {
  const res = await fetch(`${API}?ref=${BRANCH}`, { headers: await ghHeaders() })
  if (res.status === 404) return { subs: [], sha: '' }
  const json = await res.json()
  const content = Buffer.from(json.content, 'base64').toString('utf-8')
  return { subs: JSON.parse(content), sha: json.sha }
}

async function writeSubs(subs: object[], sha: string, message: string) {
  const content = Buffer.from(JSON.stringify(subs, null, 2)).toString('base64')
  await fetch(API, {
    method: 'PUT',
    headers: await ghHeaders(),
    body: JSON.stringify({ message, content, sha: sha || undefined, branch: BRANCH }),
  })
}

export async function POST(req: NextRequest) {
  const sub = await req.json()
  if (!sub?.endpoint) return NextResponse.json({ error: 'Invalid subscription' }, { status: 400 })

  const { subs, sha } = await readSubs()
  if (!subs.some((s: any) => s.endpoint === sub.endpoint)) {
    subs.push(sub)
    await writeSubs(subs, sha, 'chore: push subscription 추가')
  }
  return NextResponse.json({ ok: true })
}

export async function DELETE(req: NextRequest) {
  const { endpoint } = await req.json()
  if (!endpoint) return NextResponse.json({ error: 'Missing endpoint' }, { status: 400 })

  const { subs, sha } = await readSubs()
  const filtered = subs.filter((s: any) => s.endpoint !== endpoint)
  await writeSubs(filtered, sha, 'chore: push subscription 제거')
  return NextResponse.json({ ok: true })
}
