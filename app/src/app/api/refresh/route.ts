import { NextResponse } from 'next/server'

const REPO = 'JubroPark/ma3-momentum'

async function dispatch(workflow: string) {
  return fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.GH_PAT}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref: 'main' }),
  })
}

export async function POST() {
  const [live, eod] = await Promise.all([dispatch('live.yml'), dispatch('eod.yml')])
  if (!live.ok && !eod.ok) {
    return NextResponse.json({ error: 'workflow dispatch failed' }, { status: 500 })
  }
  return NextResponse.json({ ok: true })
}
