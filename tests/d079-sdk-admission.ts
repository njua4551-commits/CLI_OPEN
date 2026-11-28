import { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { join } from "node:path"
import { strict as assert } from "node:assert"
import { OpenCode, AbsolutePath, Location } from "@opencode/sdk/effect"
import { makeMemoryDriver } from "@opencode/core/environment/index"
import { Effect } from "effect"
import { createTaskHost } from "../implementacion/supervisor/task_sdk"

const home = mkdtempSync("/tmp/cli-open-sdk-admission-")
const path = join(home, "native.sqlite")
const options = {
  database: { path },
  config: {
    directory: home, project: false, claude: false,
    content: JSON.stringify({ permissions: [{ action: "*", resource: "*", effect: "deny" }] }),
  },
  models: { fetch: false },
  fs: { filewatcher: false, fff: false },
  fetch: async () => { throw new Error("network is disabled for the synthetic fixture") },
}
const driver = {
  create: () => Effect.succeed({ binding: {} }),
  connect: () => Effect.succeed(makeMemoryDriver()),
  suspendForIdle: () => Effect.void,
  destroy: () => Effect.void,
}

try {
  const id = await Effect.runPromise(Effect.scoped(Effect.gen(function* () {
    const host = yield* OpenCode.create(options)
    const session = yield* host.sessions.create({
      location: Location.Ref.make({ directory: AbsolutePath.make(home) }),
    })
    return session.id
  })))
  using db = new Database(path, { strict: true })
  const suspended = db.query("SELECT time_suspended, resume_attempts FROM session_v2 WHERE id = ?")
  // Seed an exhausted native claim. The real startup sweep will terminalize
  // it without invoking a model or tool.
  db.run("UPDATE session_v2 SET time_suspended = ?, resume_attempts = 10 WHERE id = ?", [Date.now(), id])
  const claim = suspended.get(id)
  assert.ok(claim)

  await assert.rejects(Effect.runPromise(Effect.scoped(createTaskHost(options, "owned", driver, ({ get }) =>
    Effect.gen(function* () {
      assert.equal((yield* get({ sessionID: id })).id, id)
      yield* Effect.sleep("150 millis")
      assert.deepEqual(suspended.get(id), claim)
      return yield* Effect.fail(new Error("task policy rejected"))
    }),
  ))), /task policy rejected/)
  assert.deepEqual(suspended.get(id), claim)

  const interrupted = await Effect.runPromise(Effect.scoped(
    createTaskHost(options, "owned", driver, () => Effect.interrupt).pipe(Effect.exit),
  ))
  assert.equal(interrupted._tag, "Failure")
  assert.deepEqual(suspended.get(id), claim)

  await Effect.runPromise(Effect.scoped(Effect.gen(function* () {
    yield* createTaskHost(options, "owned", driver, () => Effect.sync(() => {
      assert.deepEqual(suspended.get(id), claim)
    }))
    for (let attempt = 0; attempt < 100; attempt++) {
      if ((suspended.get(id) as { time_suspended: number | null }).time_suspended === null) return
      yield* Effect.sleep("20 millis")
    }
    throw new Error("native recovery did not run after admission")
  })))
  console.log("PASS native SDK startup recovery waits for task admission")
} finally {
  rmSync(home, { recursive: true, force: true })
}
