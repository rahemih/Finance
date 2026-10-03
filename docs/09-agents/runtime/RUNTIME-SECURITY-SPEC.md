# Runtime Security & Tool-Abuse Specification

## Trust model

Treat model output, web content, documents, email, chat, market commentary, plugin responses and third-party tool text as untrusted data unless a governed system contract explicitly marks a field as control metadata.

## Controls

- allowlist tools per agent and task;
- least-privilege permissions;
- deny ambient credential inheritance;
- never expose secrets to model-visible text unless the future security design explicitly requires and protects it;
- separate read tools from mutating tools;
- require typed arguments and output validation;
- validate target resource, scope and authority before mutations;
- attach idempotency keys to future side-effecting operations;
- sanitize/limit file and path writes;
- block instruction-following from retrieved content;
- cap retries and tool-call loops;
- record tool trace and security decision refs;
- circuit-break repeated failures/anomalous tool usage.

## Financial firewall

No agent or specialist may open/fund accounts, transfer/withdraw assets, increase permissions, enable Live Trading or Auto Trading, or bypass A5/A8/Human Gates unless a later explicit governed task grants that exact authority.

## Supply-chain gate

Frameworks, MCP servers, plugins and dependencies remain candidates until P02-F/P04 governance validates version, license, provenance, security posture and operational maturity.
