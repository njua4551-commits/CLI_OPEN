# CLI_OPEN

CLI_OPEN adapts a pinned OpenCode engine for supervised local development. The current checkout provides isolated workspace review and Git publication, an authenticated loopback inference gateway with persistent task budgets, and selective project memory. It is a development checkout. Installable releases and a supervised remote provider are pending.

## Develop and test

Use Git and Python 3.11 or later. The portable profile also uses Node.js 18 or later and ripgrep for its JavaScript and path-discovery fixtures. The full Linux and OpenCode profiles require an unprivileged Linux x86-64 user, working Bubblewrap namespaces, loopback sockets, and the tools reported by the supervisor. The suspended-restart fixture uses Linux PID file descriptors to signal only the synthetic native process it owns.

```sh
python3 -I -B implementacion/supervisor doctor
python3 -I -B tests/run-suite.py portable
python3 -I -B tests/run-suite.py linux
python3 -I -B tests/run-suite.py opencode
```

The OpenCode profile pins OpenCode v2.3.2 at revision `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` and Bun 1.4.4. It checks executable SHA-256 values before running either executable. The prepared source belongs at `.fase1/opencode`, the CLI at `.fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode`, and Bun at `.fase1/tools/bun-linux-x64-baseline/bun`. For a fresh Linux test checkout, run:

```sh
git clone --no-checkout https://github.com/anomalyco/opencode.git .fase1/opencode
git -C .fase1/opencode checkout --detach c0ad18b402eb2827fc1ee71c171b1177b3fc02d1
python3 -I -B tests/provision-engine.py
(
  cd .fase1/opencode
  test "$(git hash-object bun.lock)" = 0ea44ccaa17fcfccbc057839ae8aa8fe31e38af3
  ../tools/bun-linux-x64-baseline/bun install --frozen-lockfile --ignore-scripts
)
```

The provisioner verifies archive sizes and SHA-256 checksums before extraction. It verifies the executable hashes before installation. The embedded SDK fixture uses the pinned source and its frozen dependency graph. See [acquisition and build evidence](docs/PRUEBAS.md) for the original pinned build and [the upstream release](https://github.com/anomalyco/opencode/releases/tag/v2.3.2) for distribution artifacts.

The test profiles use synthetic inputs and providers. The Linux profile exercises the private namespace and real HTTP clients on loopback. The OpenCode profile also exercises the CLI and the native SDK when its dependencies are present. Hosted runner capabilities and real model inference have separate acceptance criteria.

## Gateway deadlines

The HTTP listener defaults to five seconds of client inactivity and ten seconds for the entire request to be parsed. Set `CLI_OPEN_GATEWAY_CLIENT_IDLE_SECONDS` and `CLI_OPEN_GATEWAY_PARSE_SECONDS` independently. The upstream inactivity timeout is configured with `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS`. An authenticated task still has its own absolute deadline and cumulative budget. Its streaming request is cancelled when the downstream disconnects.

## Project documentation

- [Current state](ESTADO.md) and [continuity](CONTINUAR.md)
- [Roadmap and acceptance gates](PLAN_PARA_CODEX.md)
- [Technical report](INFORME_TECNICO.md) and [architecture decisions](docs/DECISIONES.md)
- [Regression evidence](docs/PRUEBAS.md) and [change history](docs/CAMBIOS.md)
- [Threat model and supported boundaries](SECURITY.md)
