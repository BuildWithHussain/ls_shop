import { computed, effectScope, ref } from 'vue'
import { useAdminAction } from './api'

// One useCall per method, not one call over a mutable url: a shared call aborts the
// in-flight request and hands every caller the same `data`. The scope is detached
// because these requests outlive whichever component first reached for the endpoint.
export function createAdminCaller(modulePath) {
  const scope = effectScope(true)
  const requests = new Map()
  const pending = ref(0)

  function requestFor(method) {
    let request = requests.get(method)
    if (!request) {
      request = scope.run(() => useAdminAction(modulePath + method))
      requests.set(method, request)
    }
    return request
  }

  // Both halves of the outcome: a screen that must tell a refusal from a genuinely
  // empty answer needs the error handed back, not only toasted.
  async function attempt(method, params = {}) {
    const request = requestFor(method)
    pending.value += 1
    try {
      // `submit` resolves null on a failed request instead of rejecting, so the
      // refusal is read off the call. useAdminAction has already toasted it.
      const data = await request.submit(params)
      const error = request.error ?? null
      if (error) return { data: null, error }
      return { data, error: null }
    } finally {
      pending.value -= 1
    }
  }

  // Resolves to the endpoint's answer, or null when it refused.
  async function call(method, params = {}) {
    const { data } = await attempt(method, params)
    return data
  }

  return { attempt, call, loading: computed(() => pending.value > 0) }
}
