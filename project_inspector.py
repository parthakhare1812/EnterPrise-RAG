
import ast
import json
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "project_inspection_report.md"

IGNORED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "site-packages", "dist", "build",
    "vector_store", "uploads", "models", "checkpoints",
    ".pytest_cache", ".mypy_cache"
}

IGNORED_FILES = {
    ".env", ".env.local", ".env.production",
    "project_inspection_report.md"
}

SOURCE_EXTENSIONS = {".py", ".txt", ".toml", ".ini", ".cfg", ".yaml", ".yml", ".json"}

def safe_read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[Unable to read: {type(exc).__name__}]"

def discover_files():
    files = []
    for current, dirs, filenames in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)

        for filename in sorted(filenames):
            path = Path(current) / filename

            if filename in IGNORED_FILES:
                continue

            if path.suffix.lower() in SOURCE_EXTENSIONS:
                files.append(path)

    return sorted(files)

def project_tree(files):
    lines = [ROOT.name + "/"]
    for path in files:
        lines.append("  " + str(path.relative_to(ROOT)).replace("\\", "/"))
    return lines

def inspect_python(path):
    content = safe_read(path)
    result = {
        "path": str(path.relative_to(ROOT)),
        "imports": [],
        "classes": [],
        "functions": [],
        "syntax_error": None
    }

    if content.startswith("[Unable to read:"):
        result["syntax_error"] = content
        return result

    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                result["imports"].extend(alias.name for alias in node.names)

            elif isinstance(node, ast.ImportFrom):
                result["imports"].append(node.module or "")

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                result["classes"].append(node.name)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result["functions"].append(node.name)

    except SyntaxError as exc:
        result["syntax_error"] = f"Line {exc.lineno}: {exc.msg}"

    return result

def inspect_dependencies(files):
    names = {
        "requirements.txt", "pyproject.toml", "Pipfile",
        "poetry.lock", "environment.yml"
    }

    output = []
    for path in files:
        if path.name in names:
            output.append(
                f"\n### {path.relative_to(ROOT)}\n"
                f"```text\n{safe_read(path)[:12000]}\n```"
            )
    return output

def inspect_config_names(files):
    keywords = (
        "AWS_", "BEDROCK", "PINECONE", "DATABASE_URL",
        "NEON", "RIUS", "UPLOAD_", "MODEL_", "OLLAMA",
        "LANGGRAPH", "EMBEDDING"
    )

    findings = []

    for path in files:
        if path.suffix.lower() != ".py" and path.name != ".env.example":
            continue

        content = safe_read(path)

        for line_number, line in enumerate(content.splitlines(), 1):
            if any(keyword in line.upper() for keyword in keywords):
                findings.append(
                    f"- `{path.relative_to(ROOT)}` line {line_number}: "
                    f"`{line.strip()[:180]}`"
                )

    return findings

def main():
    files = discover_files()
    python_files = [p for p in files if p.suffix.lower() == ".py"]

    python_reports = [inspect_python(p) for p in python_files]

    lines = [
        "# Enterprise RAG - Project Inspection Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Project root: `{ROOT}`",
        "",
        "## 1. Project Statistics",
        "",
        f"- Source/config files: {len(files)}",
        f"- Python files: {len(python_files)}",
        "",
        "## 2. Project Structure",
        "",
        "```text",
        *project_tree(files),
        "```",
        "",
        "## 3. Python File Analysis",
        ""
    ]

    for report in python_reports:
        lines.extend([
            f"### `{report['path']}`",
            f"- Imports: {', '.join(sorted(set(report['imports'])))}",
            f"- Classes: {', '.join(report['classes'])}",
            f"- Functions: {', '.join(report['functions'])}",
        ])

        if report["syntax_error"]:
            lines.append(f"- Syntax/read issue: {report['syntax_error']}")

        lines.append("")

    lines.extend([
        "## 4. Dependency Files",
        "",
        *inspect_dependencies(files),
        "",
        "## 5. External Service and Configuration References",
        "",
        *inspect_config_names(files),
        "",
        "## 6. Important Notes",
        "",
        "- This report does not contain environment variable values.",
        "- `.env` and secret files are excluded.",
        "- Virtual environments, caches, uploads and model directories are excluded.",
        "- Application code is inspected as text and is not executed.",
        "- Large binary files are not included.",
        ""
    ])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print("\nInspection completed successfully.")
    print(f"Source files inspected: {len(files)}")
    print(f"Python files inspected: {len(python_files)}")
    print(f"Report created: {OUTPUT}")

if __name__ == "__main__":
    main()
