# Great Generator MCP examples

These examples show how to connect the optional Great Generator MCP server to local MCP-compatible clients.

Install MCP support:

```bash
pip install "great-generator[mcp]"
```

Start the server manually:

```bash
great-generator-mcp
```

Alternative module form:

```bash
python -m great_generator.mcp.server
```

## Claude Desktop

Use `claude_desktop_config.json` as a starting point:

```json
{
  "mcpServers": {
    "great-generator": {
      "command": "great-generator-mcp",
      "args": []
    }
  }
}
```

Alternative when you prefer the Python module entry point:

```json
{
  "mcpServers": {
    "great-generator": {
      "command": "python",
      "args": ["-m", "great_generator.mcp.server"]
    }
  }
}
```

If you use a virtual environment, replace `great-generator-mcp` or `python` with the full executable path from that environment.

## Cursor

Use `cursor_mcp_config.json` as a generic starting point. Adjust the file location and executable paths for your Cursor version and workspace.

## Example prompts

```text
Use Great Generator to generate 10,000 synthetic customer records from this schema and save them as CSV in ./synthetic/customers.
```

```text
Use Great Generator to parse this Databricks CREATE TABLE statement and summarize the columns.
```

```text
Generate relational test data for customers and orders. Save one CSV file per table.
```

```text
Generate data that includes region SOUTH and product types CHECKING and SAVINGS. Spread rows across these business dates.
```

```text
Validate whether the generated dataset contains the required query values and partition dates.
```

## Safety defaults

The MCP server writes generated datasets to local files, returns small previews and summaries, and does not overwrite existing files unless `overwrite=True`.

By default, paths must stay under the current working directory. Set `GREAT_GENERATOR_MCP_ALLOWED_ROOT` when you need a different local workspace.
