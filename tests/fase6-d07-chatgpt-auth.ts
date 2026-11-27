import assert from "node:assert/strict"
import { randomUUID } from "node:crypto"
import { lstat, mkdtemp, realpath, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { isAbsolute, join, sep } from "node:path"

const brave = process.argv[3]
const retainParent = process.argv[4] === "--retain" ? process.argv[5] : undefined
assert(process.argv.length === 3 || (brave && isAbsolute(brave) &&
  (process.argv.length === 4 || (process.argv.length === 6 && retainParent && isAbsolute(retainParent)))))
async function profileParent() {
  if (!retainParent) return tmpdir()
  const info = await lstat(retainParent)
  assert(info.isDirectory() && info.uid === process.getuid?.() && (info.mode & 0o077) === 0,
    "Choose a private, user-owned profile directory")
  const parent = await realpath(retainParent)
  const repo = await realpath(join(import.meta.dir, ".."))
  assert(parent !== repo && !parent.startsWith(repo + sep), "Keep the native profile outside the repository")
  return parent
}
const home = await mkdtemp(join(await profileParent(), "cli-open-auth-"))
let retain = false
const password = randomUUID()
const server = Bun.spawn([process.argv[2], "serve", "--hostname", "127.0.0.1", "--port", "0"], {
  cwd: home, stdout: "pipe", stderr: "inherit", env: {
    PATH: "/usr/bin:/bin", HOME: home, XDG_DATA_HOME: join(home, "data"), XDG_CONFIG_HOME: join(home, "config"),
    XDG_STATE_HOME: join(home, "state"), XDG_CACHE_HOME: join(home, "cache"),
    OPENCODE_PASSWORD: password, OPENCODE_DISABLE_MODELS_FETCH: "true", OPENCODE_CONFIG_PROJECT_DISABLE: "true",
    OPENCODE_CONFIG_CONTENT: JSON.stringify({ permissions: [{ action: "*", resource: "*", effect: "deny" }] }),
  },
})
const startup = setTimeout(() => server.kill("SIGKILL"), 10_000)
try {
  let baseURL = ""
  let stdout = ""
  for await (const chunk of server.stdout.pipeThrough(new TextDecoderStream())) {
    stdout += chunk
    baseURL = stdout.match(/server listening on (http:\/\/127\.0\.0\.1:\d+)/)?.[1] ?? ""
    if (baseURL) break
  }
  clearTimeout(startup)
  assert(baseURL, "Native loopback server did not start")

  async function api(path: string, method = "GET", body?: object, status = 200) {
    const result = await fetch(baseURL + "/api/" + path, {
      method, signal: AbortSignal.timeout(5_000),
      headers: { Authorization: "Basic " + btoa("opencode:" + password), "content-type": "application/json" },
      ...(body && { body: JSON.stringify(body) }),
    })
    // Do not print the raw response or attempt URL on assertion failure.
    assert.equal(result.status, status, method + " " + path.split("/").slice(0, 2).join("/"))
    if (status === 204 || status === 404) return undefined
    return (await result.json()).data
  }

  const providers = await api("provider")
  const models = await api("model")
  assert(Array.isArray(providers) && Array.isArray(models))
  assert(!providers.some((entry: { id: string }) => entry.id === "openai"))
  assert(!models.some((entry: { providerID: string }) => entry.providerID === "openai"))
  const integrations = await api("integration")
  const integration = integrations.find((entry: { id: string }) => entry.id === "openai")
  assert(integration, "OpenAI integration is absent from the native catalog")
  assert.equal(integration.id, "openai")
  assert.equal(integration.connections.length, 0)
  const method = integration.methods.find((method: { label: string }) => method.label === "Sign in with ChatGPT")
  assert.equal(method?.type, "oauth")

  const connection = "integration/openai/connect/oauth"
  const attempt = await api(connection, "POST", { methodID: method.id })
  assert.equal(attempt.mode, "auto")
  const url = new URL(attempt.url)
  assert.equal(url.origin, "https://auth.openai.com")
  assert.equal(url.searchParams.get("code_challenge_method"), "S256")
  const callback = new URL(url.searchParams.get("redirect_uri") ?? "")
  assert.equal(callback.hostname, "127.0.0.1")
  assert.equal(callback.pathname, "/auth/callback")
  assert(Number(callback.port) > 0)
  const attemptPath = connection + "/" + encodeURIComponent(attempt.attemptID)
  try {
    assert.equal((await api(attemptPath)).status, "pending")
    if (brave) {
      // Keep the authorization URL out of the terminal and reuse Brave's default profile.
      const browser = Bun.spawn([brave, url.href], { stdin: "ignore", stdout: "ignore", stderr: "ignore" })
      browser.unref()
      console.log("Brave handoff requested. Complete authorization in the browser.")
      const deadline = Date.now() + 180_000
      while (Date.now() < deadline) {
        assert(browser.exitCode === null || browser.exitCode === 0, "Browser launcher failed")
        const state = (await api(attemptPath)).status
        if (state === "complete") {
          const connected = await api("integration/openai")
          assert(connected.connections.length > 0, "OpenCode reports no connected account")
          const available = (await api("model"))
            .filter((entry: { providerID: string }) => entry.providerID === "openai")
            .map((entry: { id: string }) => entry.id)
          console.log(JSON.stringify({ authenticated: true, openaiModels: available }))
          break
        }
        assert(state === "pending", "OAuth did not complete")
        await Bun.sleep(1000)
      }
      assert.equal((await api(attemptPath)).status, "complete", "Browser consent timed out")
    }
  } finally {
    await api(attemptPath, "DELETE", undefined, 204)
  }
  if (!brave) {
    await api(attemptPath, "GET", undefined, 404)
    assert.equal((await api("integration/openai")).connections.length, 0)
    console.log("PASS native ChatGPT method and local OAuth preparation/cancellation before browser handoff")
  }
  retain = Boolean(retainParent)
} finally {
  clearTimeout(startup)
  server.kill("SIGKILL")
  await server.exited
  if (retain) console.log(JSON.stringify({ nativeProfile: home }))
  else await rm(home, { recursive: true, force: true })
}
