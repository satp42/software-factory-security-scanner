# software-factory-security-scanner

**Lens 1 of an alignment-aware security assessment engine for 8090's Software Factory.**

`sf-scan` is a CLI that maps dependency-tree vulnerabilities to a Software Factory Knowledge Graph (PRD → Feature node → Blueprint → Work Order → Code), so security findings carry business intent rather than appearing as a flat CVE list. A typical scan report tells you *"package P at version V has CVE-X."* `sf-scan` also tells you **which PRD requirement that CVE puts at risk, which Blueprint owns the remediation, and which Work Order brought the dependency in.**

The full architecture sketch for the broader four-lens engine — including Lens 4 (Work-Order-to-Code trace completeness) and the federated-learning-backdoor framing that anchors the alignment-debt research direction — lives in [`docs/architecture.md`](docs/architecture.md).

---

## Install

Requires Python 3.11+ and `git`.

```bash
git clone https://github.com/satwik/software-factory-security-scanner.git
cd software-factory-security-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

That puts `sf-scan` on PATH. Confirm with:

```bash
sf-scan --version    # prints "sf-scan 0.1.0"
sf-scan scan --help  # shows the scan-command flag surface
```

## Run

End-to-end against 8090's public [`software-factory-plugin`](https://github.com/8090-inc/software-factory-plugin) plus a deliberately-vulnerable secondary target ([OWASP NodeGoat](https://github.com/OWASP/NodeGoat)) to demonstrate the multi-target capability and produce a findings-rich report:

```bash
./examples/scan-command.sh
```

…or manually:

```bash
sf-scan scan \
  --repo https://github.com/8090-inc/software-factory-plugin \
  --repo https://github.com/OWASP/NodeGoat \
  --kg ./kg/software-factory-plugin \
  --out ./reports
```

Outputs:

- `./reports/report.md` — human-readable: executive summary, risk-prioritized action list, findings nested by PRD → Feature → Blueprint → Work Order, and a separate "Unmapped Findings" section for findings whose package is not declared in any Work Order.
- `./reports/report.json` — machine-readable: same content as a structured object, suitable for downstream automation.

## Sample output

A pre-generated sample lives at [`examples/sample-report.md`](examples/sample-report.md). Excerpt from the executive summary:

> - **Total findings:** 135
>   - Mapped to Knowledge Graph: 4
>   - Unmapped (KG coverage gap): 131
>
> **Findings by severity:** CRITICAL 15 · HIGH 71 · MEDIUM 36 · LOW 12
>
> **Ontology levels at risk:** 1 PRD (PRD-001) · 1 Feature (F-001) · 1 Blueprint (BP-001) · 1 Work Order (WO-002)
>
> **Risk-prioritized action list:**
> 1. `json-schema@0.2.3` — CRITICAL → upgrade to `0.4.0`. Affects PRD-001 / WO-002.
> 2. `semver@5.7.0` — HIGH → upgrade to `7.5.2`. Affects PRD-001 / WO-002.
> 3. `ajv@6.10.0` — MEDIUM → upgrade to `8.18.0`. Affects PRD-001 / WO-002.

The Unmapped Findings section flags the remaining 131 CVEs as packages declared by no Work Order in the Knowledge Graph — itself the structural shape that Lens 4 (alignment-debt scoring) is designed to quantify.

## How it works

Five components run in sequence:

1. **Fetch.** Each `--repo` URL (optionally `URL@SHA` pinned) is cloned into a temp directory.
2. **Extract.** Manifest parsers for npm (`package.json`, `package-lock.json`), PyPI (`requirements.txt`, `pyproject.toml`), Go modules (`go.mod`), and RubyGems (`Gemfile.lock`) walk the cloned tree and produce a normalized list of `(ecosystem, package, version)` tuples. Lockfile entries win over manifest entries when both exist.
3. **Query.** OSV.dev's batch API resolves CVEs across the aggregate dependency list. Results are cached in `~/.cache/sf-scan/vuln-cache.db` with a 24-hour TTL; bypass with `--no-cache`. OSV.dev aggregates the GitHub Advisory Database, so GHSA-prefixed findings carry both source tags.
4. **Resolve.** Each finding's `(ecosystem, package)` is matched against every Work Order's `dependencies-introduced` field. Matches walk upward through the Work Order's `blueprint` → Blueprint's `feature` (or `product` for foundation blueprints) → Feature's `product` → PRD. Findings with no match land in the "Unmapped" bucket.
5. **Render.** `report.md` and `report.json` are emitted to `--out`. The Markdown nests headings by ontology level with relative links to every KG artifact file.

See [`docs/architecture.md`](docs/architecture.md) for the full four-lens engine architecture and the alignment-debt research bridge.

## Status

| Lens | What it measures | Status |
|------|------------------|--------|
| **1. Dependency CVE → Ontology** | npm/PyPI/Go/Ruby dependency vulnerabilities, mapped to the KG. | **Shipped (this repo).** |
| 2. Requirements-to-Test Coverage | Whether every Acceptance Example in a PRD has a corresponding test. | Sketched in [docs/architecture.md](docs/architecture.md). |
| 3. Blueprint-to-Code Drift | Whether shipped code reflects each Blueprint's stated architectural decisions. | Sketched. |
| 4. Work-Order-to-Code Trace Completeness | Scalar alignment-debt score per Work Order; aggregates to per-edge KG drift. **Bridges to federated-learning backdoor research.** | Sketched with a directional scoring formula. |

## Provenance and IP

The `kg/software-factory-plugin/` directory is a **synthetic Knowledge Graph** authored by Satwik for demo purposes, structured to follow 8090's publicly documented [Requirements Writing Guide](https://www.8090.ai/docs/opinions/requirements-writing-guide), [Blueprint Writing Guide](https://www.8090.ai/docs/opinions/blueprint-writing-guide), and [Work Order Writing Guide](https://www.8090.ai/docs/opinions/work-order-writing-guide). It is **not** real 8090 product data and was never produced by 8090's Software Factory. See [`kg/software-factory-plugin/README.md`](kg/software-factory-plugin/README.md) for the full provenance disclaimer.

The scanner itself is original code under the [MIT License](LICENSE). All inputs to the demo run (sf-plugin, NodeGoat, the synthetic KG, OSV.dev, the GitHub Advisory Database) are public.

## Development

Run the test suite:

```bash
pytest
```

Run network-dependent tests (live OSV.dev + GitHub clone):

```bash
SF_SCAN_NETWORK_TESTS=1 pytest
```

129 unit and integration tests live in `tests/`. Two more are network-dependent and opt-in.

## License

MIT. See [`LICENSE`](LICENSE).
