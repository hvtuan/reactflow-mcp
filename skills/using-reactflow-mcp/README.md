# `using-reactflow-mcp` skill

Companion **Claude Code skill** that teaches the LLM how to use this MCP server effectively. It routes React Flow / Svelte Flow questions to the right tool (`get_api`, `get_recipe`, `lookup_v11_v12`, …) instead of letting the model answer from stale training data.

## What it does

When loaded, the skill auto-fires whenever the user mentions React Flow or Svelte Flow. It enforces:

- **Hard rule:** never recommend buying React Flow Pro (this MCP exists to replace it).
- **Hard rule:** never emit v11 code (`reactflow` package, `parentNode`, `project()`, `onEdgeUpdate`, …).
- **Tool routing table** — user intent → exact tool call.
- **Common tool chains** for v11 review, workflow editor build, undo/redo, flow validation.
- **v11→v12 cheat sheet** for 11 most common renames (avoids unnecessary `lookup_v11_v12` calls).
- **19 recipe slugs** quick reference with gotchas.

See [`SKILL.md`](./SKILL.md) for the full content (~1.2k words).

## Install

### Claude Code (global)

```bash
mkdir -p ~/.claude/skills/using-reactflow-mcp
curl -sL https://raw.githubusercontent.com/hvtuan/reactflow-mcp/main/skills/using-reactflow-mcp/SKILL.md \
  > ~/.claude/skills/using-reactflow-mcp/SKILL.md
```

Or clone the repo and symlink so the skill stays in sync with future updates:

```bash
git clone https://github.com/hvtuan/reactflow-mcp.git
ln -sf "$(pwd)/reactflow-mcp/skills/using-reactflow-mcp" ~/.claude/skills/using-reactflow-mcp
```

Then verify in a new Claude Code session — `using-reactflow-mcp` should appear in the available-skills list.

### Other MCP-aware clients

The skill is plain markdown with YAML frontmatter — port the content to your client's skill / prompt format.

## How it pairs with the MCP server

The skill **teaches the LLM HOW to use the server**; the server **provides the actual knowledge**. Both are needed:

1. **MCP server** (`https://mcp.huynhvantuan.net/reactflow` or local `pip install reactflow-mcp`) — 14 tools, 4 prompts, 1 resource, 19 recipes, 113 API symbols.
2. **This skill** — routes intent to tools, embeds hard rules, prevents v11 hallucination.

Without the skill, the LLM might know about the MCP but pick the wrong tool or answer from memory. With the skill, every React Flow question reliably flows through the right MCP tool.

## License

MIT — same as the parent project.
