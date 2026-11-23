import { profiles } from '../scripts/network-profile.mjs'

export const experimentProfiles = {
  stable: { opening: 'stable' },
  slow: { opening: 'slow' },
  intermittent: { opening: 'stable', marking: 'offline', edits: ['offline', 'offline', 'stable', 'stable', 'offline'], checkout: 'offline' },
  offline: { opening: 'offline' },
}

export async function networkFor(...pages) {
  const sessions = await Promise.all(pages.map(page => page.context().newCDPSession(page)))
  return async name => {
    await Promise.all(sessions.map(session => session.send(
      'Network.emulateNetworkConditions', profiles[name][0].conditions,
    )))
    return performance.now()
  }
}
