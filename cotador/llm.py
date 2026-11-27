# -*- coding: utf-8 -*-
"""Chamada ao Claude com saída estruturada (JSON Schema).

Dois motores com a mesma interface:
- ClaudeCLI: usa o Claude Code instalado na máquina (`claude -p`). Não precisa de chave de API. É o que roda no protótipo.
- ClaudeAPI: usa a API da Anthropic com ANTHROPIC_API_KEY. É o caminho de produção (não testado nesta versão).
"""
import json, os, shutil, subprocess, tempfile, time, urllib.request


class ClaudeCLI:
    def __init__(self, modelo="sonnet", tentativas=2):
        self.exe = shutil.which("claude")
        if not self.exe:
            raise RuntimeError("Claude Code não encontrado no PATH.")
        # No Windows o npm instala um claude.CMD, e o cmd.exe corta argumentos com quebra de linha.
        # Chamamos o executável real que o .CMD aponta.
        if self.exe.lower().endswith(".cmd"):
            real = os.path.join(os.path.dirname(self.exe), "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")
            if os.path.exists(real):
                self.exe = real
        self.modelo, self.tentativas = modelo, tentativas

    def estruturar(self, sistema: str, entrada: str, schema: dict) -> tuple[dict, dict]:
        cmd = [self.exe, "-p", "--system-prompt", sistema, "--tools", "", "--strict-mcp-config",
               "--no-session-persistence", "--model", self.modelo, "--output-format", "json",
               "--json-schema", json.dumps(schema, ensure_ascii=False)]
        erro = None
        for _ in range(self.tentativas):
            t0 = time.time()
            # cwd neutro para não carregar instruções de projeto (CLAUDE.md) no contexto
            r = subprocess.run(cmd, input=entrada, capture_output=True, text=True, encoding="utf-8",
                               cwd=tempfile.gettempdir(), timeout=300)
            try:
                d = json.loads(r.stdout)
                saida = d.get("structured_output") or json.loads(d["result"])
                meta = {"segundos": round(time.time() - t0, 1), "custo_usd": d.get("total_cost_usd"),
                        "tokens_entrada": d["usage"]["input_tokens"] + d["usage"].get("cache_creation_input_tokens", 0)
                        + d["usage"].get("cache_read_input_tokens", 0),
                        "tokens_saida": d["usage"]["output_tokens"], "motor": f"claude-cli/{self.modelo}"}
                return saida, meta
            except Exception as e:  # saída malformada: tenta de novo
                erro = f"{e}: {r.stdout[:300]} {r.stderr[:300]}"
        raise RuntimeError(f"Falha na chamada ao Claude: {erro}")


class ClaudeAPI:
    """Mesmo contrato via API (tool use forçado para garantir o esquema)."""
    def __init__(self, modelo="claude-sonnet-5-5"):
        self.chave = os.environ["ANTHROPIC_API_KEY"]
        self.modelo = modelo

    def estruturar(self, sistema, entrada, schema):
        corpo = {"model": self.modelo, "max_tokens": 4096, "system": sistema,
                 "messages": [{"role": "user", "content": entrada}],
                 "tools": [{"name": "registrar", "description": "Registra a cotação estruturada", "input_schema": schema}],
                 "tool_choice": {"type": "tool", "name": "registrar"}}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(corpo).encode(),
                                     headers={"x-api-key": self.chave, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        t0 = time.time()
        d = json.loads(urllib.request.urlopen(req, timeout=300).read())
        bloco = next(b for b in d["content"] if b["type"] == "tool_use")
        return bloco["input"], {"segundos": round(time.time() - t0, 1), "motor": f"api/{self.modelo}",
                                "tokens_entrada": d["usage"]["input_tokens"], "tokens_saida": d["usage"]["output_tokens"]}


def motor_padrao():
    """COTADOR_LLM=cli|api escolhe o motor; sem ela, usa a API se houver ANTHROPIC_API_KEY, senão o Claude Code."""
    escolha = os.environ.get("COTADOR_LLM", "").lower()
    if escolha == "api" or (not escolha and os.environ.get("ANTHROPIC_API_KEY")):
        return ClaudeAPI()
    return ClaudeCLI()
