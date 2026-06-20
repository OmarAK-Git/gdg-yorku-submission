import ast
import os
import uuid
from typing import Dict, List, Tuple, Any, Callable
from gdg_yorku_submission.schemas import ReviewFinding, Location, CorpusFile
from gdg_yorku_submission.severity import Severity

SUPPORTED_EXTS = {".py"}
IGNORE_EXTS = {
    "", ".md", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".gitignore", ".env", ".ini", ".cfg", ".conf", ".lock", ".csv",
    ".gitkeep", ".gitattributes", ".dockerignore"
}


def detect_languages(corpus: Dict[str, CorpusFile]) -> Tuple[List[str], int]:
    """
    Detects unsupported languages in the prompt-exposed corpus.
    Returns (unsupported_languages, unsupported_language_count).
    """
    unsupported = set()
    for path, corpus_file in corpus.items():
        if corpus_file.exposure_status != "prompt_exposed":
            continue
        _, ext = os.path.splitext(path.lower())
        if ext not in SUPPORTED_EXTS and ext not in IGNORE_EXTS:
            unsupported.add(ext.lstrip("."))
            
    sorted_unsupported = sorted(list(unsupported))
    return sorted_unsupported, len(sorted_unsupported)


def is_literal(node: ast.AST) -> bool:
    """Checks if an AST node is a literal constant."""
    node_type = type(node).__name__
    if node_type == "Constant":
        return True
    if node_type in {"Str", "Num", "Bytes", "NameConstant"}:
        return True
    if isinstance(node, (ast.List, ast.Tuple)):
        return all(is_literal(el) for el in node.elts)
    if isinstance(node, ast.Dict):
        return all(is_literal(k) and is_literal(v) for k, v in zip(node.keys, node.values) if k is not None)
    return False


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, corpus_file: CorpusFile):
        self.file_path = file_path
        self.corpus_file = corpus_file
        self.findings: List[ReviewFinding] = []
        # Trace imported names to avoid bare name false positives (Issue 8)
        self.imports: Dict[str, str] = {}

    def add_finding(self, node: ast.AST, claim: str, rule: str, severity: Severity = Severity.HIGH):
        # Map line numbers using the corpus_file mapping
        start_line = self.corpus_file.map_line(node.lineno)
        end_line = self.corpus_file.map_line(getattr(node, "end_lineno", None) or node.lineno)
        
        # Non-prose discriminator: ast-node-id (rule + lineno + col_offset)
        col_offset = getattr(node, "col_offset", 0)
        ast_node_id = f"ast-{rule}-{start_line}-{col_offset}"
        
        prov_id = f"provisional-security-{uuid.uuid4()}"
        
        location = Location(
            path=self.file_path,
            line_start=start_line,
            line_end=end_line
        )
        
        finding = ReviewFinding(
            id=prov_id,
            source_agent="security_deterministic",
            perspective="security",
            severity=severity,
            location=location,
            claim=claim,
            evidence_ref=[f"file:{self.file_path}#{start_line}-{end_line}"],
            status="active",
            metadata={
                "rule_or_category": "security_baseline",
                "sub_rule": rule,
                "ast_node_id": ast_node_id,
                "evidence_anchor": ast_node_id
            }
        )
        self.findings.append(finding)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imports[asname] = name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imports[asname] = f"{module}.{name}"
        self.generic_visit(node)

    def is_sqli_arg(self, node: ast.AST) -> bool:
        if isinstance(node, ast.JoinedStr):
            for val in node.values:
                if isinstance(val, ast.FormattedValue):
                    if not is_literal(val.value):
                        return True
            return False
            
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            def check_concat(n):
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                    return check_concat(n.left) or check_concat(n.right)
                if isinstance(n, (ast.JoinedStr, ast.Call)):
                    return self.is_sqli_arg(n)
                return not is_literal(n)
            return check_concat(node)
            
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
                if not is_literal(node.func.value):
                    return True
                for arg in node.args:
                    if not is_literal(arg):
                        return True
                for kw in node.keywords:
                    if not is_literal(kw.value):
                        return True
                return False
                
        return False

    def is_write_decorator(self, dec: ast.AST) -> bool:
        """Checks if a decorator is a write route decorator (POST/PUT/PATCH/DELETE)."""
        dec_func = dec
        if isinstance(dec, ast.Call):
            dec_func = dec.func
            
        attr_name = ""
        if isinstance(dec_func, ast.Attribute):
            attr_name = dec_func.attr
        elif isinstance(dec_func, ast.Name):
            attr_name = dec_func.id
            
        if attr_name in {"post", "put", "patch", "delete"}:
            return True
            
        if attr_name == "route":
            # Flask route: check methods keyword argument
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == "methods":
                        if isinstance(kw.value, (ast.List, ast.Tuple)):
                            for el in kw.value.elts:
                                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                    if el.value.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                                        return True
                                elif type(el).__name__ == "Str":
                                    if getattr(el, "s", "").upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                                        return True
        return False

    def is_route_decorator(self, dec: ast.AST) -> bool:
        """Checks if a decorator is any Flask/FastAPI route decorator."""
        dec_func = dec
        if isinstance(dec, ast.Call):
            dec_func = dec.func
            
        attr_name = ""
        if isinstance(dec_func, ast.Attribute):
            attr_name = dec_func.attr
        elif isinstance(dec_func, ast.Name):
            attr_name = dec_func.id
            
        if attr_name in {"route", "get", "post", "put", "delete", "patch", "head", "options", "trace"}:
            return True
        return False

    def is_auth_depends_call(self, node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
            
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
        if func_name != "Depends":
            return False
            
        if node.args:
            dep_func = node.args[0]
            dep_name = ""
            if isinstance(dep_func, ast.Name):
                dep_name = dep_func.id
            elif isinstance(dep_func, ast.Attribute):
                dep_name = dep_func.attr
                
            dep_name_lower = dep_name.lower()
            # Expanded auth decorator/dependency vocab (Issue 10)
            auth_terms = {
                "auth", "login", "jwt", "session", "permission", "user", "cred", "token", 
                "protect", "admin", "role", "guard"
            }
            if any(term in dep_name_lower for term in auth_terms):
                return True
        return False

    def check_route_auth(self, node: ast.FunctionDef) -> bool:
        """Returns True if the route handler function has authentication."""
        for dec in node.decorator_list:
            if self.is_write_decorator(dec):
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if kw.arg == "dependencies":
                            if isinstance(kw.value, (ast.List, ast.Tuple)):
                                for dep in kw.value.elts:
                                    if self.is_auth_depends_call(dep):
                                        return True
                continue
                
            dec_name = ""
            if isinstance(dec, ast.Call):
                dec_func = dec.func
            else:
                dec_func = dec
                
            if isinstance(dec_func, ast.Name):
                dec_name = dec_func.id
            elif isinstance(dec_func, ast.Attribute):
                dec_name = dec_func.attr
                
            dec_name_lower = dec_name.lower()
            # Expanded auth decorator vocab (Issue 10)
            auth_terms = {
                "auth", "login", "jwt", "session", "permission", "require", "guard", 
                "protect", "admin", "role", "user"
            }
            if any(term in dec_name_lower for term in auth_terms):
                return True
                
        # Check function parameters defaults
        defaults = node.args.defaults
        arg_defaults = {}
        if defaults:
            offset = len(node.args.args) - len(defaults)
            for idx, default in enumerate(defaults):
                param_name = node.args.args[offset + idx].arg
                arg_defaults[param_name] = default
                
        for param in node.args.kwonlyargs:
            idx = node.args.kwonlyargs.index(param)
            if idx < len(node.args.kw_defaults) and node.args.kw_defaults[idx] is not None:
                arg_defaults[param.arg] = node.args.kw_defaults[idx]
                
        for default_node in arg_defaults.values():
            if self.is_auth_depends_call(default_node):
                return True
                
        return False

    def check_path_traversal(self, node: ast.FunctionDef):
        # Parameters of the function are initially tainted
        initial_tainted = {arg.arg for arg in node.args.args + node.args.kwonlyargs}
        
        # We walk the AST to track assignment taint and match path traversal calls.
        # This resolves under-firing (intermediate variable assignments and function-global suppression)
        # and over-firing (collision with standard string .join() calls).
        visitor_self = self
        
        class PathTaintVisitor(ast.NodeVisitor):
            def __init__(self, initial):
                self.tainted = set(initial)
                self.safe = set()
                self.vuln_nodes = []
                self.suppressed_nodes = set()

            def is_node_tainted(self, n: ast.AST) -> bool:
                if isinstance(n, ast.Name):
                    return n.id in self.tainted and n.id not in self.safe
                if isinstance(n, ast.Attribute):
                    # request.args.get() etc
                    if isinstance(n.value, ast.Name) and n.value.id == "request":
                        return True
                    return self.is_node_tainted(n.value)
                if isinstance(n, ast.Subscript):
                    return self.is_node_tainted(n.value)
                if isinstance(n, ast.BinOp):
                    return self.is_node_tainted(n.left) or self.is_node_tainted(n.right)
                if isinstance(n, ast.JoinedStr):
                    return any(isinstance(v, ast.FormattedValue) and self.is_node_tainted(v.value) for v in n.values)
                if isinstance(n, ast.Call):
                    # Path(user_input) is tainted if user_input is tainted
                    func_name = ""
                    if isinstance(n.func, ast.Name):
                        func_name = n.func.id
                    elif isinstance(n.func, ast.Attribute):
                        func_name = n.func.attr
                    if func_name in {"Path", "join", "joinpath"}:
                        # Check if it is os.path.join or path.join or from os.path import join
                        is_std_path_join = False
                        if func_name == "join":
                            receiver_str = ""
                            if isinstance(n.func, ast.Attribute):
                                parts = []
                                curr = n.func.value
                                while isinstance(curr, ast.Attribute):
                                    parts.append(curr.attr)
                                    curr = curr.value
                                if isinstance(curr, ast.Name):
                                    parts.append(curr.id)
                                parts.reverse()
                                receiver_str = ".".join(parts)
                            resolved_recv = visitor_self.imports.get(receiver_str, receiver_str)
                            if resolved_recv in {"os.path", "path"} or visitor_self.imports.get("join") == "os.path.join":
                                is_std_path_join = True
                        else:
                            is_std_path_join = True

                        if is_std_path_join:
                            return any(self.is_node_tainted(arg) for arg in n.args) or (
                                isinstance(n.func, ast.Attribute) and self.is_node_tainted(n.func.value)
                            )
                return False

            def visit_Assign(self, assign_node: ast.Assign):
                val = assign_node.value
                is_normalized = False
                
                # Check if it's a normalization call: abspath, realpath, resolve
                if isinstance(val, ast.Call):
                    func_name = ""
                    if isinstance(val.func, ast.Name):
                        func_name = val.func.id
                    elif isinstance(val.func, ast.Attribute):
                        func_name = val.func.attr
                        
                    if func_name in {"resolve", "abspath", "realpath"}:
                        tainted_arg = any(self.is_node_tainted(arg) for arg in val.args)
                        tainted_recv = False
                        if isinstance(val.func, ast.Attribute):
                            tainted_recv = self.is_node_tainted(val.func.value)
                        if tainted_arg or tainted_recv:
                            is_normalized = True
                            
                targets = []
                for target in assign_node.targets:
                    if isinstance(target, ast.Name):
                        targets.append(target.id)
                        
                if is_normalized:
                    for t in targets:
                        self.safe.add(t)
                else:
                    val_tainted = self.is_node_tainted(val)
                    for t in targets:
                        if val_tainted:
                            self.tainted.add(t)
                        else:
                            self.tainted.discard(t)
                            self.safe.discard(t)
                            
                self.generic_visit(assign_node)

            def visit_Call(self, call_node: ast.Call):
                func_name = ""
                resolved_recv = ""
                
                if isinstance(call_node.func, ast.Attribute):
                    parts = []
                    curr = call_node.func.value
                    while isinstance(curr, ast.Attribute):
                        parts.append(curr.attr)
                        curr = curr.value
                    if isinstance(curr, ast.Name):
                        parts.append(curr.id)
                    parts.reverse()
                    receiver_str = ".".join(parts)
                    resolved_recv = visitor_self.imports.get(receiver_str, receiver_str)
                    func_name = call_node.func.attr
                elif isinstance(call_node.func, ast.Name):
                    func_name = call_node.func.id
                    
                is_path_call = False
                if func_name in {"open", "Path", "joinpath"}:
                    is_path_call = True
                elif func_name == "join":
                    if resolved_recv in {"os.path", "path"} or visitor_self.imports.get("join") == "os.path.join":
                        is_path_call = True
                        
                if is_path_call:
                    is_flagged = False
                    for arg in call_node.args:
                        if self.is_node_tainted(arg):
                            is_flagged = True
                            break
                    if not is_flagged:
                        for kw in call_node.keywords:
                            if self.is_node_tainted(kw.value):
                                is_flagged = True
                                break
                    
                    if is_flagged:
                        if call_node not in self.suppressed_nodes:
                            self.vuln_nodes.append(call_node)
                        # Suppress double-reporting nested calls (Issue 11, point 1)
                        for arg in call_node.args:
                            if isinstance(arg, ast.Call):
                                self.suppressed_nodes.add(arg)
                        for kw in call_node.keywords:
                            if isinstance(kw.value, ast.Call):
                                self.suppressed_nodes.add(kw.value)
                            
                # Check for startswith validation
                if func_name == "startswith" and isinstance(call_node.func, ast.Attribute):
                    obj = call_node.func.value
                    if isinstance(obj, ast.Name) and obj.id in self.tainted:
                        self.safe.add(obj.id)
                        
                self.generic_visit(call_node)

            def visit_Compare(self, comp_node: ast.Compare):
                # Check for ".." in var validation
                has_dotdot = False
                for op in comp_node.ops:
                    if isinstance(op, ast.In):
                        if isinstance(comp_node.left, ast.Constant) and isinstance(comp_node.left.value, str) and ".." in comp_node.left.value:
                            has_dotdot = True
                        elif type(comp_node.left).__name__ == "Str" and ".." in getattr(comp_node.left, "s", ""):
                            has_dotdot = True
                            
                if has_dotdot:
                    for comparator in comp_node.comparators:
                        if isinstance(comparator, ast.Name) and comparator.id in self.tainted:
                            self.safe.add(comparator.id)
                                
                self.generic_visit(comp_node)

        taint_visitor = PathTaintVisitor(initial_tainted)
        taint_visitor.visit(node)
        
        for vuln_node in taint_visitor.vuln_nodes:
            self.add_finding(
                vuln_node,
                claim="Path traversal risk: request input is used directly in a path open or join operation without a normalize-and-root check.",
                rule="path_traversal"
            )

    def visit_Call(self, node: ast.Call):
        func_name = ""
        receiver = ""
        
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                receiver = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name):
                receiver = node.func.value.attr
            
        # SQLi check
        if func_name in {"execute", "executemany", "execute_async"}:
            sql_arg = None
            if node.args:
                sql_arg = node.args[0]
            else:
                for kw in node.keywords:
                    if kw.arg in {"query", "sql", "statement"}:
                        sql_arg = kw.value
                        break
            if sql_arg and self.is_sqli_arg(sql_arg):
                self.add_finding(
                    node,
                    claim="SQL Injection risk: DB execute call receives a non-literal query expression constructed with f-string, concat, or format.",
                    rule="sqli"
                )

        # shell=True check
        if func_name in {"run", "Popen", "call", "check_call", "check_output"}:
            shell_true = False
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    shell_true = True
                    break
                elif kw.arg == "shell" and type(kw.value).__name__ == "NameConstant" and kw.value.value is True:
                    shell_true = True
                    break
            if shell_true:
                cmd_arg = node.args[0] if node.args else None
                if not cmd_arg:
                    for kw in node.keywords:
                        if kw.arg == "args":
                            cmd_arg = kw.value
                            break
                if cmd_arg and not is_literal(cmd_arg):
                    self.add_finding(
                        node,
                        claim="Command injection risk: subprocess call with shell=True receives a non-literal command argument.",
                        rule="shell_true"
                    )

        # HEURISTIC TRADE-OFF: 'from os import system; system(cmd)' is a rare false negative due to 'os' not being directly in imports.
        if func_name in {"system", "popen"} and (receiver == "os" or receiver == "" and "os" in self.imports.values()):
            cmd_arg = node.args[0] if node.args else None
            if not cmd_arg:
                for kw in node.keywords:
                    if kw.arg == "command":
                        cmd_arg = kw.value
                        break
            if cmd_arg and not is_literal(cmd_arg):
                self.add_finding(
                    node,
                    claim="Command injection risk: os call executes a non-literal command argument.",
                    rule="shell_true"
                )

        # Unsafe deserialization check (Issue 8 import tracking)
        if func_name in {"load", "loads"}:
            resolved_module = ""
            if receiver:
                resolved_module = self.imports.get(receiver, receiver)
            else:
                resolved_path = self.imports.get(func_name, "")
                if "." in resolved_path:
                    resolved_module = resolved_path.rsplit(".", 1)[0]
                
            is_pickle = (resolved_module == "pickle")
            is_yaml = (resolved_module == "yaml" and func_name == "load")
                
            if is_pickle or is_yaml:
                data_arg = node.args[0] if node.args else None
                if data_arg and not is_literal(data_arg):
                    if is_pickle:
                        self.add_finding(
                            node,
                            claim="Unsafe deserialization risk: pickle load/loads called on non-literal data.",
                            rule="unsafe_deserialize"
                        )
                    elif is_yaml:
                        has_safe_loader = False
                        for kw in node.keywords:
                            if kw.arg == "Loader":
                                val_name = ""
                                if isinstance(kw.value, ast.Name):
                                    val_name = kw.value.id
                                elif isinstance(kw.value, ast.Attribute):
                                    val_name = kw.value.attr
                                if "SafeLoader" in val_name:
                                    has_safe_loader = True
                        if not has_safe_loader:
                            self.add_finding(
                                node,
                                claim="Unsafe deserialization risk: yaml.load called without SafeLoader on non-literal data.",
                                rule="unsafe_deserialize"
                            )

        # verify=False check (Issue 9 precision constraint)
        # HEURISTIC TRADE-OFF: matching on receiver names 'session/client/http' may false-positive if a local non-HTTP variable is named session/client/http.
        is_http_call = False
        if receiver:
            resolved_recv = self.imports.get(receiver, receiver)
            if resolved_recv in {"requests", "httpx", "session", "client", "http"} or resolved_recv.startswith("requests.") or resolved_recv.startswith("httpx."):
                is_http_call = True
        else:
            resolved_func = self.imports.get(func_name, "")
            if resolved_func.startswith("requests.") or resolved_func.startswith("httpx."):
                is_http_call = True
            elif func_name in {"get", "post", "put", "delete", "patch", "request", "head", "options"}:
                # If get/post is called directly and we have an import of requests/httpx
                if any(val == m or val.startswith(m + ".") for val in self.imports.values() for m in {"requests", "httpx"}):
                    is_http_call = True
                
        if is_http_call:
            for kw in node.keywords:
                is_false = False
                if kw.arg == "verify":
                    if isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        is_false = True
                    elif type(kw.value).__name__ == "NameConstant" and kw.value.value is False:
                        is_false = True
                if is_false:
                    self.add_finding(
                        node,
                        claim="SSL verification disabled: HTTP call contains verify=False.",
                        rule="verify_false"
                    )
                    break

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        is_route = False
        is_write = False
        for dec in node.decorator_list:
            if self.is_route_decorator(dec):
                is_route = True
            if self.is_write_decorator(dec):
                is_write = True
                
        if is_route:
            if is_write and not self.check_route_auth(node):
                self.add_finding(
                    node,
                    claim="Missing authorization: HTTP write route lacks any auth decorator or dependency.",
                    rule="missing_auth"
                )
            self.check_path_traversal(node)
            
        self.generic_visit(node)


def make_security_specialist(orch: Any) -> Callable[[], Tuple[List[ReviewFinding], str, str]]:
    """
    Returns the specialist function running the deterministic security baseline AST scan.
    """
    def security_specialist() -> Tuple[List[ReviewFinding], str, str]:
        corpus = orch.get_corpus()
        
        # 1. Language detection
        unsupported_langs, unsupported_count = detect_languages(corpus)
        
        # 2. Run AST scan
        findings = []
        unparseable_files = []
        
        for rel_path, corpus_file in corpus.items():
            # Restrict to prompt_exposed files only (Issue 13)
            if corpus_file.exposure_status != "prompt_exposed":
                continue
                
            _, ext = os.path.splitext(rel_path.lower())
            if ext == ".py" and corpus_file.redacted_text:
                try:
                    tree = ast.parse(corpus_file.redacted_text)
                    visitor = SecurityVisitor(rel_path, corpus_file)
                    visitor.visit(tree)
                    findings.extend(visitor.findings)
                except SyntaxError:
                    unparseable_files.append(rel_path)
                except Exception:
                    unparseable_files.append(rel_path)
                    
        # Update metadata in orchestrator cleanly via seam (Issue 11)
        orch.set_run_metadata("unsupported_language_count", unsupported_count)
        orch.set_run_metadata("unparseable_file_count", len(unparseable_files))
        
        # Determine status and reason based on both unsupported languages and unparseable files (Issue 5 & 13)
        reasons = []
        if unsupported_langs:
            reasons.append(f"no deterministic rules for {', '.join(unsupported_langs)}")
        if unparseable_files:
            reasons.append(f"syntax errors in {', '.join(sorted(unparseable_files))}")
            
        if reasons:
            status = "complete_limited"
            reason = "; ".join(reasons)
        else:
            status = "complete"
            reason = ""
            
        return findings, status, reason
        
    return security_specialist
