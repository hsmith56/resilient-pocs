#!/usr/bin/env python3
"""Minimal interactive CRUD CLI for a Python ruleset variable."""

from __future__ import annotations

import argparse
import ast
import copy
import datetime as _dt
import json
import pprint
import shutil
import sys
from pathlib import Path
from typing import Any


class RulesCliError(Exception):
    pass


class SafeResolver(ast.NodeVisitor):
    """Resolve Python literals plus earlier literal assignments by name."""

    def __init__(self, names: dict[str, Any] | None = None):
        self.names = {} if names is None else names

    def resolve(self, node: ast.AST) -> Any:
        return self.visit(node)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(item) for item in node.elts)

    def visit_Set(self, node: ast.Set) -> set[Any]:
        return {self.visit(item) for item in node.elts}

    def visit_Dict(self, node: ast.Dict) -> dict[Any, Any]:
        out: dict[Any, Any] = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise RulesCliError("dict unpacking is not supported")
            out[self.visit(key)] = self.visit(value)
        return out

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        value = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.Not):
            return not value
        raise RulesCliError(f"unsupported unary op: {type(node.op).__name__}")

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.names:
            return copy.deepcopy(self.names[node.id])
        raise RulesCliError(f"unresolved name {node.id!r}; only literal assignments can be resolved")

    def generic_visit(self, node: ast.AST) -> Any:
        raise RulesCliError(f"unsupported syntax in ruleset: {type(node).__name__}")


def node_span(text: str, node: ast.AST) -> tuple[int, int]:
    if not all(hasattr(node, attr) for attr in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        raise RulesCliError("Python AST lacks end positions; use Python 3.8+")
    lines = text.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[: node.end_lineno - 1]) + node.end_col_offset
    return start, end


def assigned_name(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                return target.id
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    return None


def assigned_value(stmt: ast.stmt) -> ast.AST | None:
    if isinstance(stmt, ast.Assign):
        return stmt.value
    if isinstance(stmt, ast.AnnAssign):
        return stmt.value
    return None


def load_rules(path: Path, var_name: str) -> tuple[str, ast.AST, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        raise RulesCliError(f"cannot parse Python file: {exc}") from exc

    names: dict[str, Any] = {}
    resolver = SafeResolver(names)
    target_node: ast.AST | None = None

    for stmt in tree.body:
        name = assigned_name(stmt)
        value = assigned_value(stmt)
        if name is None or value is None:
            continue
        if name == var_name:
            target_node = value
            break
        try:
            names[name] = resolver.resolve(value)
        except RulesCliError:
            pass

    if target_node is None:
        raise RulesCliError(f"variable {var_name!r} not found")
    rules = SafeResolver(names).resolve(target_node)
    return text, target_node, rules


def render_rules(rules: Any) -> str:
    return pprint.pformat(rules, width=100, sort_dicts=False)


def clear_screen() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def pause() -> None:
    if sys.stdin.isatty():
        input("\npress Enter...")


def pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except TypeError:
        return pprint.pformat(obj, width=100, sort_dicts=False)


def print_title(text: str) -> None:
    print(text)
    print("=" * len(text))


def print_main_menu(path: Path, var_name: str, dirty: bool) -> None:
    print_title("Rules CLI")
    print(f"file: {path}")
    print(f"var:  {var_name}")
    print(f"state: {'unsaved changes' if dirty else 'clean'}")
    print()
    print("1. View rules")
    print("2. Select/update rule")
    print("3. Create rule")
    print("4. Delete rule")
    print("5. Priority clashes")
    print("6. Validate")
    print("7. Save")
    print("8. Quit")


def backup_path(path: Path) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.name}.bak-{stamp}")


def save_rules(path: Path, original_text: str, node: ast.AST, rules: Any) -> Path:
    start, end = node_span(original_text, node)
    rendered = render_rules(rules)
    new_text = original_text[:start] + rendered + original_text[end:]
    backup = backup_path(path)
    shutil.copy2(path, backup)
    path.write_text(new_text, encoding="utf-8")
    return backup


def rule_label(rule: Any, index: int) -> str:
    if isinstance(rule, dict):
        name = rule.get("name", "<no name>")
        priority = rule.get("priority", "<no priority>")
        return f"{index}: priority={priority} name={name}"
    return f"{index}: {type(rule).__name__}"


def view_rules(rules: Any) -> None:
    if not isinstance(rules, list):
        print(f"ruleset is {type(rules).__name__}, not list")
        print(pprint.pformat(rules, sort_dicts=False))
        return
    for i, rule in enumerate(rules):
        print(rule_label(rule, i))


def choose_rule(rules: Any) -> int | None:
    if not isinstance(rules, list) or not rules:
        print("no rules")
        return None
    view_rules(rules)
    raw = input("rule index/name: ").strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 0 <= idx < len(rules):
            return idx
        print("bad index")
        return None
    matches = [
        i
        for i, rule in enumerate(rules)
        if isinstance(rule, dict) and raw.lower() in str(rule.get("name", "")).lower()
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        print("multiple matches:")
        for i in matches:
            print(rule_label(rules[i], i))
    else:
        print("no match")
    return None


def parse_value(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        raise RulesCliError("empty value")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError) as exc:
        raise RulesCliError("value must be JSON or Python literal") from exc


def input_multiline(prompt: str) -> str:
    print(prompt)
    print("finish with a line containing only .")
    lines: list[str] = []
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines)


def create_rule(rules: Any) -> bool:
    if not isinstance(rules, list):
        print("create requires list ruleset")
        return False
    raw = input_multiline("new rule dict (JSON/Python literal):")
    try:
        rule = parse_value(raw)
    except RulesCliError as exc:
        print(exc)
        return False
    if not isinstance(rule, dict):
        print("rule must be dict")
        return False
    rules.append(rule)
    print("created")
    return True


def update_rule(rule: Any) -> bool:
    if not isinstance(rule, dict):
        print("update supports dict rules only")
        return False
    while True:
        clear_screen()
        print_title("Rule actions")
        print(f"name:     {rule.get('name', '<no name>')}")
        print(f"priority: {rule.get('priority', '<no priority>')}")
        print()
        print(pretty(rule))
        print()
        print("1. View details")
        print("2. Set field")
        print("3. Delete field")
        print("4. Replace rule")
        print("5. Back")
        choice = input("> ").strip()
        if choice == "1":
            print()
            print(pretty(rule))
            pause()
        elif choice == "2":
            key = input("field: ").strip()
            if not key:
                print("missing field")
                pause()
                continue
            raw = input("value (JSON/Python literal): ")
            try:
                rule[key] = parse_value(raw)
            except RulesCliError as exc:
                print(exc)
                pause()
                continue
            print("updated")
            return True
        elif choice == "3":
            key = input("field: ").strip()
            if key in rule:
                del rule[key]
                print("deleted")
                return True
            print("missing field")
            pause()
        elif choice == "4":
            raw = input_multiline("replacement rule dict (JSON/Python literal):")
            try:
                replacement = parse_value(raw)
            except RulesCliError as exc:
                print(exc)
                pause()
                continue
            if not isinstance(replacement, dict):
                print("replacement must be dict")
                pause()
                continue
            rule.clear()
            rule.update(replacement)
            print("replaced")
            return True
        elif choice == "5":
            return False
        else:
            print("bad choice")
            pause()


def delete_rule(rules: Any) -> bool:
    idx = choose_rule(rules)
    if idx is None:
        return False
    print(pretty(rules[idx]))
    if input("delete this rule? [y/N] ").strip().lower() == "y":
        del rules[idx]
        print("deleted")
        return True
    return False


def priority_clashes(rules: Any) -> list[str]:
    if not isinstance(rules, list):
        return ["ruleset is not list"]
    groups: dict[Any, list[str]] = {}
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        groups.setdefault(rule.get("priority"), []).append(rule_label(rule, i))
    messages: list[str] = []
    for priority, labels in sorted(groups.items(), key=lambda item: str(item[0])):
        if priority is not None and len(labels) > 1:
            messages.append(f"priority {priority}:\n  " + "\n  ".join(labels))
    return messages


def validate(rules: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(rules, list):
        return ["ruleset must be a list"]
    seen_names: dict[str, int] = {}
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rule {i}: must be dict")
            continue
        name = rule.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"rule {i}: missing/non-string name")
        elif name in seen_names:
            errors.append(f"rule {i}: duplicate name also at {seen_names[name]}")
        else:
            seen_names[name] = i
        priority = rule.get("priority")
        if not isinstance(priority, (int, float)) or isinstance(priority, bool):
            errors.append(f"rule {i}: missing/non-number priority")
        conditions = rule.get("conditions")
        if conditions is not None and not isinstance(conditions, dict):
            errors.append(f"rule {i}: conditions must be dict")
        if "assignment" in rule and not isinstance(rule["assignment"], (dict, str)):
            errors.append(f"rule {i}: assignment must be dict or str")
    return errors


def print_messages(title: str, messages: list[str]) -> None:
    print_title(title)
    if messages:
        for msg in messages:
            print(f"- {msg}")
    else:
        print("none")


def interactive(path: Path, var_name: str, original_text: str, node: ast.AST, rules: Any) -> int:
    dirty = False
    while True:
        clear_screen()
        print_main_menu(path, var_name, dirty)
        choice = input("> ").strip()
        if choice == "1":
            clear_screen()
            print_title("Rules")
            view_rules(rules)
            pause()
        elif choice == "2":
            clear_screen()
            print_title("Select rule")
            idx = choose_rule(rules)
            if idx is not None and update_rule(rules[idx]):
                dirty = True
                pause()
        elif choice == "3":
            clear_screen()
            print_title("Create rule")
            changed = create_rule(rules)
            dirty = changed or dirty
            pause()
        elif choice == "4":
            clear_screen()
            print_title("Delete rule")
            changed = delete_rule(rules)
            dirty = changed or dirty
            pause()
        elif choice == "5":
            clear_screen()
            print_messages("Priority clashes", priority_clashes(rules))
            pause()
        elif choice == "6":
            clear_screen()
            print_messages("Validation errors", validate(rules))
            pause()
        elif choice == "7":
            clear_screen()
            print_title("Save")
            if not dirty:
                print("no changes")
                pause()
                continue
            backup = save_rules(path, original_text, node, rules)
            original_text, node, rules = load_rules(path, var_name)
            dirty = False
            print(f"saved\nbackup: {backup}")
            pause()
        elif choice == "8":
            if dirty and input("unsaved changes; quit anyway? [y/N] ").strip().lower() != "y":
                continue
            return 0
        else:
            print("bad choice")
            pause()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CRUD CLI for a Python ruleset variable")
    parser.add_argument("--input", required=True, help="Python script containing ruleset variable")
    parser.add_argument("--var-name", default="ROUTING_RULES", help="ruleset variable name")
    args = parser.parse_args(argv)

    path = Path(args.input)
    if not path.exists():
        print(f"input not found: {path}", file=sys.stderr)
        return 2
    try:
        original_text, node, rules = load_rules(path, args.var_name)
    except RulesCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return interactive(path, args.var_name, original_text, node, rules)


if __name__ == "__main__":
    raise SystemExit(main())
