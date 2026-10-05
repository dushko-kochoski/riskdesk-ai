# Dependency Security Audit

Audit date: 2026-10-05

## Scope and result

The frontend was checked with npm's advisory database using the committed lockfile. The initial result was 15 findings: 11 high, one moderate, and three low. Running the compatible, non-forced remediation updated the lockfile within the existing version ranges and reduced the result to five high findings. No `npm audit fix --force` or major dependency upgrade was used.

The browser application has no affected runtime package. React and React DOM are the only production dependencies, and `npm audit --omit=dev --audit-level=high` reports zero vulnerabilities. Vite, TypeScript, the React plugin, Tailwind, PostCSS, ESLint, and their transitive packages are correctly classified as development/build dependencies. They execute while developing, linting, or producing static assets; they are not included as server-side code in the deployed browser bundle.

## Compatible fixes applied

| Package | Severity | Updated version | Use and exploit conditions |
| --- | --- | --- | --- |
| `@babel/core` | Low | 7.29.0 → 7.29.7 | React build tooling. A malicious `sourceMappingURL` processed during a local build could read a local file. [GHSA-4x5r-pxfx-6jf8](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8) |
| `baseline-browser-mapping` | Moderate | 2.10.27 → 2.11.27 | Browser-target build data. Invalid attacker-controlled input could terminate the build process. [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv) |
| `brace-expansion` | High | 1.1.14 → 1.1.21; 5.0.5 → 5.0.12 | ESLint and TypeScript-ESLint glob handling. Crafted glob ranges or nested groups could exhaust CPU, memory, or the stack. The repository uses static developer-owned patterns. [GHSA-q2hr-2g5m-vwhr](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr), [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7) |
| `browserslist` | High | 4.28.2 → 4.29.3 | Autoprefixer/Babel build targeting. Large sets of untrusted queries or hostile custom statistics could cause memory exhaustion, a crash, or prototype writes. This project uses static build configuration. [GHSA-c83g-rgw3-j3cx](https://github.com/advisories/GHSA-c83g-rgw3-j3cx), [GHSA-73wf-gq98-2v4g](https://github.com/advisories/GHSA-73wf-gq98-2v4g) |
| `esbuild` | Low | 0.27.7 → 0.28.2 | Vite compiler and development server. On Windows, an attacker with local access to a reachable development server could abuse crafted paths to read files. The project binds Vite to loopback, but the package was still patched. [GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr) |
| `js-yaml` | High | 4.1.1 → 4.3.2 | ESLint configuration parsing. Hostile YAML containing alias, merge-key, or ordered-map structures could consume excessive CPU. The application does not accept YAML from users. [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh), [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) |
| `nanoid` | High | 3.3.12 → 3.3.20 | Transitive PostCSS utility. Invalid negative or zero sizes passed to particular generators could loop indefinitely; the application does not call those generators. [GHSA-28wg-ghj8-5hjv](https://github.com/advisories/GHSA-28wg-ghj8-5hjv), [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) |
| `postcss` | High | 8.5.14 → 8.5.29 | CSS build pipeline. A crafted source-map comment in attacker-controlled CSS could traverse paths and disclose local map files during a build. Project CSS is repository-controlled. [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849), [GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp) |
| `postcss-selector-parser` | Low | 6.1.2 → 6.1.4 | Tailwind/PostCSS selector parsing. Deeply nested attacker-controlled selectors could cause recursion denial of service. Project CSS is repository-controlled. [GHSA-w9m9-85wc-3x92](https://github.com/advisories/GHSA-w9m9-85wc-3x92) |
| `vite` | High | 7.3.2 → 7.3.6 | Local development server/build tool. On Windows, specially formed alternate paths could bypass file-deny rules, and a crafted editor path could disclose an NTLMv2 hash. Exploitation requires access to the development server or malicious development input; the production static bundle is unaffected. [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff), [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3) |

## Findings requiring a larger upgrade

The full development audit still reports five high-severity package entries: `braces@3.0.3`, `chokidar@3.6.0`, `fast-glob@3.3.3`, `micromatch@4.0.8`, and their direct parent `tailwindcss@3.4.19`. These are one transitive vulnerability chain, not five independent runtime attack surfaces. Deeply nested, attacker-controlled glob patterns can exhaust the build process stack. Risk is limited here because Tailwind scans developer-controlled source patterns during local or CI builds and none of these packages ships in the browser bundle. [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)

npm offers only `tailwindcss@4.3.3` as the complete fix, which is a semver-major migration. That work should be handled separately because Tailwind 4 changes the PostCSS integration, configuration model, and CSS entry-point conventions. It needs a deliberate configuration migration plus desktop/mobile visual regression review; forcing it into this dependency patch would create avoidable presentation risk.

## Reproduction

```powershell
cd frontend
npm ci
npm audit
npm audit --omit=dev --audit-level=high
```

Expected result for this revision: the full development audit reports the five documented Tailwind-chain entries, while the production-only audit reports zero vulnerabilities.

## Verification results

- Python 3.11 clean install from `requirements.lock` with `--require-hashes`: passed.
- Backend pytest: 34 passed; the upstream FastAPI/Starlette test client emitted one deprecation warning about the future `httpx2` package.
- Backend Ruff: passed.
- Frontend `npm ci`: passed using `package-lock.json`.
- Frontend production dependency audit: zero vulnerabilities.
- Frontend ESLint: passed.
- TypeScript/Vite production build: passed with 30 transformed modules; output remained 218.35 kB JavaScript (66.69 kB gzip) and 16.97 kB CSS (4.25 kB gzip).
- Browser flow: dashboard loaded with the backend online, the high-risk filter returned one matching case, the case-review drawer opened, and the responsive case-card/drawer layout rendered at 390 by 844 pixels. The only console error was the pre-existing missing `favicon.ico` request; no application runtime warning or error was observed.
