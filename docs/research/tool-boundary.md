# Tool Calling Boundary

Hermes karar katmanı ile Sport Toto adapterları arasına provider-neutral tool sınırı eklendi.

```text
ResearchDecision
      ↓ categories
ResearchToolRegistry
      ↓ allowlist + budget
AdapterRegistry
      ↓ provider adapter
Evidence / RetrievalResult
```

Hermes veya üst orchestrator doğrudan `OddsAdapter`/`SquadAdapter` çağırmaz. Yalnızca ResearchDecision içindeki kategorileri `tools_from_research_decision()` ile ister.

Kurallar:

- Research gerekli değilse tool çağrısı yoktur.
- Registry'de ToolSpec olmayan kategori `tool_not_allowed` döner.
- `max_attempts` aşılırsa `research_exhausted` döner.
- Adapter retrieval failure evidence değildir.
- Tool boundary adapterın iç provider ayrıntılarını dışarı sızdırmaz.
