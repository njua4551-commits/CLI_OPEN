import { join, resolve } from "node:path"
import { AbsolutePath, EnvironmentFiles, Location, Model, Provider, Session, Workspace } from "@opencode/sdk/effect"
import { makeMemoryDriver } from "@opencode/core/environment/index"
import { Effect } from "effect"
import { createTaskHost } from "./task_sdk"

// The supervisor supplies the private profile by pipe. Only offsets are appended
// to its fixed, read-only Bubblewrap command.
const settings = await Bun.stdin.json() as {
  session: string; workspace: string; directory: string; database: string
  worker: string[]; size: number; port: number; model: string; bearer: string
}
const sessionID = Session.ID.make(settings.session)
const workspaceID = Workspace.ID.make(settings.workspace)
const filename = join(settings.directory, "input.txt")
const baseURL = `http://127.0.0.1:${settings.port}/v1`
const endpoint = baseURL + "/chat/completions"
const provider = "supervised"
const model = Model.Ref.make({ providerID: Provider.ID.make(provider), id: Model.ID.make(settings.model) })
const info = { type: "file" as const, size: settings.size, mtimeMs: 0 }
let reads = 0
const deny = (path: string) => Effect.fail(new EnvironmentFiles.Failed({ path, cause: "operation unavailable" }))
const environment = {
  spawner: makeMemoryDriver().spawner,
  overrides: {
    stat: (path: string) => resolve(settings.directory, path) === filename
      ? Effect.succeed(info) : Effect.fail(new EnvironmentFiles.NotFound({ path })),
    read: (path: string, range?: { offset: number; length: number }) => {
      if (resolve(settings.directory, path) !== filename) return Effect.fail(new EnvironmentFiles.NotFound({ path }))
      return Effect.tryPromise({
        try: async (signal) => {
          const child = Bun.spawn([...settings.worker, String(range?.offset ?? 0), String(range?.length ?? info.size)], {
            stdin: "ignore", stdout: "pipe", stderr: "ignore", env: {}, signal,
          })
          const [bytes, status] = await Promise.all([child.stdout.bytes(), child.exited])
          if (status !== 0 || bytes.length > info.size) throw new Error("isolated worker failed")
          reads++
          return { info, bytes }
        },
        catch: () => new EnvironmentFiles.Failed({ path, cause: "isolated read failed" }),
      })
    },
    list: deny, write: deny, move: deny, remove: deny, mkdir: deny, append: deny,
  },
}
const bound = (id: string) => id === workspaceID
const failure = new Error("unexpected workspace binding")
const driver = {
  create: ({ workspaceID: id }: { workspaceID: string }) => bound(id)
    ? Effect.succeed({ binding: { workspaceID } }) : Effect.die(failure),
  connect: ({ workspaceID: id, binding }: { workspaceID: string; binding: Record<string, unknown> }) =>
    bound(id) && binding.workspaceID === workspaceID ? Effect.succeed(environment) : Effect.die(failure),
  suspendForIdle: () => Effect.void,
  destroy: () => Effect.void,
}

try {
  const report = await Effect.runPromise(Effect.scoped(Effect.gen(function* () {
    const host = yield* createTaskHost({
      database: { path: settings.database },
      config: {
        directory: settings.directory, project: false, claude: false,
        content: JSON.stringify({
          model: `${provider}/${settings.model}`,
          permissions: [
            { action: "*", resource: "*", effect: "deny" },
            { action: "read", resource: "input.txt", effect: "allow" },
          ],
          providers: { [provider]: {
            package: "@opencode/ai/providers/openai-compatible",
            settings: { baseURL, apiKey: settings.bearer },
            models: { [settings.model]: { capabilities: { tools: true }, limit: { context: 16000, output: 256 } } },
          } },
        }),
      },
      models: { fetch: false },
      fs: { filewatcher: false, fff: false },
      fetch: async (input, init) => {
        const request = new Request(input, init)
        if (request.url !== endpoint || request.method !== "POST") throw new Error("destination denied")
        return fetch(request, { redirect: "error" })
      },
    }, provider, driver, () => Effect.tryPromise({
      try: async (signal) => {
        const response = await fetch(endpoint, { method: "HEAD",
          headers: { Authorization: "Bearer " + settings.bearer }, signal, redirect: "error" })
        if (response.status !== 204) throw new Error("gateway authentication failed")
      },
      catch: () => new Error("gateway admission failed"),
    }))
    yield* host.workspace.create({ id: workspaceID, provider })
    const session = yield* host.sessions.create({
      id: sessionID,
      location: Location.Ref.make({ directory: AbsolutePath.make(settings.directory), workspaceID }),
    })
    if (session.id !== sessionID) throw new Error("unexpected session")
    yield* host.sessions.prompt({ sessionID, model, text: "Read input.txt and report the contents." })
    yield* host.experimental.session.wait({ sessionID })
    const history = yield* host.message.list({ sessionID })
    const parts = history.data.flatMap((message) => message.type === "assistant" ? message.content : [])
    const complete = parts.find((part) => part.type === "tool" && part.name === "read" && part.state.status === "completed")
    if (!reads || !complete || complete.type !== "tool" || complete.state.status !== "completed") {
      throw new Error("native read did not complete")
    }
    return { reads, result: complete.state.content.flatMap((part) => part.type === "text" ? [part.text] : []).join("\n").slice(0, 8000) }
  })))
  console.log(JSON.stringify(report))
} catch {
  console.error("Supervised native task failed.")
  process.exitCode = 1
}
