"""Parse the 4 Sabre Agentic OpenAPI specs -> sabre_fixtures.json (real paths + example payloads)."""
import glob, json, yaml

def resolve_ref(spec, ref):
    node = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node

def example_value(spec, content):
    """Pull a concrete example dict out of an OpenAPI content block."""
    app = (content or {}).get("application/json", {})
    if "examples" in app:
        first = next(iter(app["examples"].values()))
        if "$ref" in first:
            first = resolve_ref(spec, first["$ref"])
        return first.get("value")
    if "example" in app:
        return app["example"]
    return None

out = {}
for path in sorted(glob.glob("sabre_*.yml")):
    if "spec" in path:  # skip the renamed bm copy if present
        pass
    spec = yaml.safe_load(open(path, encoding="utf-8"))
    title = spec["info"]["title"]
    srv = spec["servers"][0]
    url_tmpl = srv["url"]
    vars_ = {k: v.get("default", "") for k, v in srv.get("variables", {}).items()}
    base = url_tmpl
    for k, v in vars_.items():
        base = base.replace("{" + k + "}", v)
    ops = {}
    for p, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            req = example_value(spec, op.get("requestBody", {}).get("content"))
            resp_ex = None
            for code in ("200", "201"):
                r = op.get("responses", {}).get(code)
                if r:
                    resp_ex = example_value(spec, r.get("content"))
                    break
            ops[op.get("operationId", method + " " + p)] = {
                "method": method.upper(), "path": p,
                "request_example": req, "response_example": resp_ex,
            }
    out[title] = {"base": base, "operations": ops}

json.dump(out, open("sabre_fixtures.json", "w", encoding="utf-8"), indent=2)

# human summary
for title, api in out.items():
    print(f"\n=== {title}\n    base: {api['base']}")
    for oid, o in api["operations"].items():
        rq = "yes" if o["request_example"] else "—"
        rs = "yes" if o["response_example"] else "—"
        print(f"    {o['method']:5} {o['path']:28} op={oid:18} req_ex={rq} resp_ex={rs}")
