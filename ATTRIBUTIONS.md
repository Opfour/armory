# Attributions

Tools, libraries, and projects that armory packages wrap, depend on, or were inspired by.

---

## Installation & Distribution

| Upstream                       | Repo                                                                    | Used by                                        |
| ------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------- |
| **skills CLI** (Vercel Labs)   | [vercel-labs/skills](https://github.com/vercel-labs/skills)             | `npx skills add` install method                |
| **agent-skills** (Vercel Labs) | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | Skill format conventions, SKILL.md spec origin |

## Direct Library & Tool Dependencies

| Upstream                                 | Repo                                                                                                          | License                   | Used by (armory skill)               |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------ |
| **Manim** (3Blue1Brown / ManimCommunity) | [3b1b/manim](https://github.com/3b1b/manim) / [ManimCommunity/manim](https://github.com/ManimCommunity/manim) | MIT                       | `concept-to-video`                   |
| **Remotion**                             | [remotion-dev/remotion](https://github.com/remotion-dev/remotion)                                             | Custom (Remotion License) | `remotion-video`                     |
| **MarkItDown** (Microsoft)               | [microsoft/markitdown](https://github.com/microsoft/markitdown)                                               | MIT                       | `to-markdown`                        |
| **notebooklm-py** (teng-lin)             | [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py)                                           | MIT                       | `notebooklm`                         |
| **yt-dlp**                               | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)                                                             | Unlicense                 | `youtube-search`, `youtube-analysis` |
| **youtube-transcript-api** (jdepoix)     | [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)                           | MIT                       | `youtube-analysis`                   |
| **Reveal.js**                            | [hakimel/reveal.js](https://github.com/hakimel/reveal.js)                                                     | MIT                       | `html-presentation`                  |
| **Lightpanda Browser**                   | [lightpanda-io/browser](https://github.com/lightpanda-io/browser)                                             | AGPL-3.0                  | `lightpanda-browser`                 |
| **agent-browser** (Lightpanda)           | [lightpanda-io/agent-skill](https://github.com/lightpanda-io/agent-skill)                                     | —                         | `lightpanda-browser`                 |
| **Tavily API**                           | [tavily-ai/tavily-python](https://github.com/tavily-ai/tavily-python)                                         | MIT                       | `tavily`                             |
| **Puppeteer** (Google)                   | [puppeteer/puppeteer](https://github.com/puppeteer/puppeteer)                                                 | Apache-2.0                | `lightpanda-browser` (CDP client)    |
| **gitleaks**                             | [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)                                                     | MIT                       | `repo-sentinel`, `secret-scanner`    |
| **arXiv API**                            | [lukasschwab/arxiv.py](https://github.com/lukasschwab/arxiv.py)                                               | MIT                       | `arxiv-search`                       |
| **pytest**                               | [pytest-dev/pytest](https://github.com/pytest-dev/pytest)                                                     | MIT                       | `test-harness`                       |
| **KaTeX**                                | [KaTeX/KaTeX](https://github.com/KaTeX/KaTeX)                                                                 | MIT                       | `md-to-pdf`                          |
| **Mermaid**                              | [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid)                                                   | MIT                       | `md-to-pdf`, `architecture-diagram`  |
| **Playwright** (Microsoft)               | [microsoft/playwright](https://github.com/microsoft/playwright)                                               | Apache-2.0                | `qa-systematic`                      |

## Conceptual Inspiration

| Concept                                        | Source                                                                                                                  | Used by                                  |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Sequential Thinking MCP Server                 | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) (sequential-thinking)                   | `sequential-thinking` (deprecated)       |
| Fetch MCP Server                               | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) (fetch)                                 | `web-fetch` (replacement)                |
| Filesystem MCP Server                          | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) (filesystem)                            | `filesystem` (replacement)               |
| Artificial Immune Systems / Negative Selection | Academic literature (Forrest, Hofmeyr, Dasgupta)                                                                        | `immune`                                 |
| Porter's Five Forces / Lean Canvas / JTBD      | Standard business frameworks                                                                                            | `competitive-analyzer`, `idea-validator` |
| OWASP Top 10                                   | [OWASP Foundation](https://owasp.org/www-project-top-ten/)                                                              | `security-reviewer`                      |
| ADR format                                     | [joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record) | `adr-writer`                             |

## Community & Research

| Source                                                                                                     | Author                                             |
| ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| [claude-code-skills](https://github.com/notmanas/claude-code-skills)                                       | [@notmanas](https://github.com/notmanas)           |
| [EvoSkills: Self-Evolving Agent Skills via Co-Evolutionary Verification](https://arxiv.org/abs/2604.01687) | Zhang, Fan, Zou, Chen et al.                       |
| [gitagent](https://github.com/open-gitagent/gitagent)                                                      | [@shreyaskapale](https://github.com/shreyaskapale) |

## Notes

- Remotion's license has commercial use restrictions. Lightpanda is AGPL-3.0 — armory wraps these as skills without distributing their binaries.
- Skills that are pure prompt engineering (e.g., `humanize`, `code-refiner`, `architecture-reviewer`) have no upstream library dependency.
- The `immune` skill's Cheatsheet/Immune pattern draws from Stephanie Forrest's original Artificial Immune Systems research.
