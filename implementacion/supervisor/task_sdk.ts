import { SessionRestart } from "@opencode/core/session/execution/restart"
import { OpenCode, WorkspaceDriver } from "@opencode/sdk/effect"
import { Deferred, Effect, Exit, Layer, Scope } from "effect"

/**
 * Internal host boundary for a supervisor-owned task. The caller must own the
 * dedicated native database and trusted configuration with other startup
 * dispatch paths disabled. Confirm that the entire native startup sweep may
 * run before returning from admit. Reject admission if any effect is uncertain.
 * Keep SDK clients and the admission callback on the trusted side.
 */
export const createTaskHost = <E, R>(
  options: Omit<OpenCode.CreateOptions, "workspaceProviders">,
  provider: string,
  driver: WorkspaceDriver.Interface,
  admit: (session: Pick<OpenCode.Interface["sessions"], "get">) => Effect.Effect<void, E, R>,
  sweep = true,
) =>
  Effect.gen(function* () {
    const admitted = yield* Deferred.make<void>()
    const ready = Deferred.await(admitted)
    const swept = yield* Deferred.make<void>()
    const gatedDriver = WorkspaceDriver.make({
      create: (input) => ready.pipe(Effect.andThen(Effect.suspend(() => driver.create(input)))),
      connect: (input) => ready.pipe(Effect.andThen(Effect.suspend(() => driver.connect(input)))),
      suspendForIdle: (input) => ready.pipe(Effect.andThen(Effect.suspend(() => driver.suspendForIdle(input)))),
      destroy: (input) => ready.pipe(Effect.andThen(Effect.suspend(() => driver.destroy(input)))),
    })
    // The SDK starts this fiber inside create(), before it returns the client.
    // Hold the entire sweep, including background jobs that can bypass a workspace driver.
    const restart = SessionRestart.node.mapLayer((layer) =>
      Layer.effect(
        SessionRestart.Service,
        Effect.map(SessionRestart.Service, (native) =>
          SessionRestart.Service.of({
            resumeSuspendedSessions: sweep
              ? ready.pipe(Effect.andThen(native.resumeSuspendedSessions),
                  Effect.onExit((exit) => Deferred.done(swept, exit)))
              : Effect.void,
          }),
        ),
      ).pipe(Layer.provide(layer)),
    )
    const scope = yield* Scope.fork(yield* Effect.scope)
    return yield* Effect.gen(function* () {
      const host = yield* OpenCode.create(
        { ...options, workspaceProviders: { [provider]: gatedDriver } },
        { overrides: [SessionRestart.node.replace(restart)] },
      )
      yield* admit({ get: host.sessions.get })
      yield* Deferred.succeed(admitted, undefined)
      return { ...host, awaitRecovery: sweep ? Deferred.await(swept) : Effect.void }
    }).pipe(
      Scope.provide(scope),
      Effect.onError((cause) => Scope.close(scope, Exit.failCause(cause))),
    )
  })
