import inspect
import malariagen_data

def build_schema_registry():
    dataset_classes = {
        "Ag3": malariagen_data.Ag3,
        "Af1": malariagen_data.Af1,
    }
    registry = {}
    for class_name, cls in dataset_classes.items():
        for method_name, method_obj in inspect.getmembers(cls):
            if method_name.startswith("_") or not inspect.isfunction(method_obj):
                continue
            try:
                sig = inspect.signature(method_obj)
                doc = inspect.getdoc(method_obj) or ""
                doc_first_line = doc.split("\n")[0].strip() if doc else ""

                params = {}
                for param_name, param_obj in sig.parameters.items():
                    if param_name == "self":
                        continue
                    param_info = {"type": str(param_obj.annotation)}
                    if param_obj.default is not inspect.Parameter.empty:
                        param_info["default"] = str(param_obj.default)
                    params[param_name] = param_info

                registry[f"{class_name}.{method_name}"] = {
                    "class": class_name,
                    "method": method_name,
                    "description": doc_first_line,
                    "parameters": params,
                    "is_plot": method_name.startswith("plot_"),
                }
            except Exception:
                pass
    return registry

SCHEMA_REGISTRY = build_schema_registry()

def build_schema_summary():
    seen = set()
    lines = []
    for entry in SCHEMA_REGISTRY.values():
        method = entry["method"]
        if method in seen:
            continue
        seen.add(method)
        params_str = ", ".join(entry["parameters"].keys()) if entry["parameters"] else ""
        desc = f'  # {entry["description"]}' if entry.get("description") else ""
        lines.append(f"- {method}({params_str}){desc}")
    return "\n".join(lines)

SCHEMA_SUMMARY = build_schema_summary()
