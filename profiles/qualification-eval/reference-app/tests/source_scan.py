"""Static scan of app/ for state-changing SQL, built to resist the disguises reviewers demonstrated (SR4-002).

The lock-discipline property is checked from the SQL each operation really runs, but WHICH functions are
operations comes from this scan. Verifier round 5 showed three ways to hide a write from it: SQL assembled
from pieces, a write in a module the scan did not open, and executescript text that does not start with a
write verb. The scan now refuses all three by being strict instead of clever:

  * every execute/executemany/executescript call in app/ must be given a string LITERAL, so SQL cannot be
    assembled, formatted or passed in a variable, and what the literal says can be read;
  * executescript is allowed in exactly one place, db.connect, applying the module constant SCHEMA;
  * every module under app/ is read, so a write in web.py or a new flat module is found, and a function
    that writes is named module.function so the caller can insist it is a covered operation;
  * leading SQL comments are skipped before the first keyword is read;
  * a statement is non-writing only if its first keyword is SELECT, BEGIN, COMMIT or ROLLBACK. Anything else
    (WITH ... INSERT, which Verifier round 11 showed writes a row, or any statement the scan does not know)
    makes its function a writer, so it must be a covered operation. The scan names writers by allowlist,
    not by a list of write verbs. A ROLLBACK is non-writing only when it is the whole statement, so
    ROLLBACK TO (which undoes rows inside a savepoint) is a write;
  * the database can be reached only through a direct call whose first argument is a string literal (Security
    round 5, SR5-001). The methods execute, executemany, executescript, backup and blobopen may appear only as
    the callee of a call; the same names as text (what methodcaller and attrgetter take) are refused; so are
    __call__, __getattribute__, __getattr__ and exec/eval as attributes, __builtins__, globals, and
    importing operator, builtins, importlib or ctypes. An alias such as run = db.execute is therefore refused
    because db.execute is not being called where it is mentioned;
  * the scan is closed, not a list of disguises (Verifier round 13, R13-002). Instead of naming the shapes
    that reach a database method without writing `.execute(`, it allows only what the app needs:
      - app/ may import only ALLOWED_MODULES and its own modules;
      - an attribute may be used only if it is in the fixed list APP_ATTRS (the names app/ gives its own
        objects) or STDLIB_ATTRS (names it uses on standard-library objects). The list is written out, not
        derived from the code: a parameter, variable or function that app/ happens to bind under a name such as
        `deserialize` (Verifier round 14, R14-001) does not make `.deserialize` allowed. So
        `logging.sys.modules`, `vars(...)["ex" + "ecute"]` and every other route that needs an attribute the
        lists do not name is refused without being named;
      - no name or attribute may be a dunder (__class__, __dict__, __get__ ...), and the introspection
        builtins in FORBIDDEN_NAMES are refused;
    so a new capability needs an edit to this file that a reviewer can see.

It is still a static scan, and it says only that the shipped code uses nothing outside that vocabulary.
"""
import ast
import pathlib
import re

NON_WRITING = ("SELECT", "BEGIN", "COMMIT", "ROLLBACK")
EXECUTE_CALLS = {"execute", "executemany", "executescript"}
DB_METHODS = EXECUTE_CALLS | {"backup", "blobopen"}
FORBIDDEN_NAMES = {"getattr", "setattr", "delattr", "hasattr", "vars", "type", "dir", "locals", "globals",
                   "eval", "exec", "compile", "open", "object", "super", "memoryview", "breakpoint", "input"}
FORBIDDEN_ATTRS = {"exec", "eval", "executemany", "backup", "blobopen"}
ALLOWED_MODULES = {"base64", "contextlib", "dataclasses", "hashlib", "hmac", "json", "logging", "math", "re",
                   "secrets", "sqlite3", "time"}
# Attribute names the app gives its own objects (functions, dataclass fields, state). Written out on purpose.
APP_ATTRS = {'TEST_SIGNING_KEY', '_body', '_dispatch', 'add_member', 'assign_ticket', 'authenticate', 'balance', 'can', 'can_grant', 'check_key', 'check_role', 'clock', 'create_ticket', 'credit', 'db', 'db_id', 'debit', 'fingerprint', 'get_ticket', 'is_active_member', 'key', 'login', 'remember', 'remove_member', 'replay', 'require', 'require_live', 'role', 'status', 'tenant_id', 'text', 'user_id'}
# Attribute names the app uses on standard-library objects. Any attribute outside these two sets is refused.
STDLIB_ATTRS = {"Row", "append", "compare_digest", "compile", "connect", "contextmanager", "count", "decode",
                "dumps", "encode", "exception", "execute", "executescript", "fetchall", "fetchone", "fromhex",
                "fullmatch", "get", "getLogger", "groups", "hex", "hexdigest", "in_transaction", "isascii",
                "isfinite", "lastrowid", "loads", "match", "new", "read", "row_factory", "rstrip", "scrypt",
                "sha256", "split", "startswith", "strip", "time", "token_bytes", "urlsafe_b64decode",
                "urlsafe_b64encode"}
_COMMENT = re.compile(r"\s*(?:--[^\n]*(?:\n|$)|/\*.*?\*/)", re.DOTALL)


def _without_leading_comments(sql):
    while True:
        match = _COMMENT.match(sql)
        if not match:
            return sql
        sql = sql[match.end():]


def first_keyword(sql):
    """The first SQL keyword, upper-cased, after any leading whitespace and comments."""
    match = re.match(r"\s*([A-Za-z]+)", _without_leading_comments(sql))
    return match.group(1).upper() if match else ""


def is_writing(sql):
    """True unless the statement is a SELECT, BEGIN, COMMIT or a bare ROLLBACK."""
    keyword = first_keyword(sql)
    if keyword not in NON_WRITING:
        return True
    if keyword == "ROLLBACK":
        words = _without_leading_comments(sql).replace(";", " ").upper().split()
        return words not in (["ROLLBACK"], ["ROLLBACK", "TRANSACTION"])
    return False


def _is_dunder(name):
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


class _Scanner(ast.NodeVisitor):
    def __init__(self, module):
        self.module, self.stack = module, []
        self.writers, self.problems = set(), []
        self.called = set()  # ids of attribute nodes that are the callee of a call

    @property
    def where(self):
        return f"{self.module}.{self.stack[-1] if self.stack else '<module>'}"

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node):
        if node.id in FORBIDDEN_NAMES or (_is_dunder(node.id) and node.id != "__name__"):
            self.problems.append(f"{self.where}: use of {node.id} hides what the code can run")

    def visit_Attribute(self, node):
        if _is_dunder(node.attr):
            self.problems.append(f"{self.where}: .{node.attr} is a dunder, which can reach what the code can run")
        elif node.attr not in APP_ATTRS and node.attr not in STDLIB_ATTRS:
            self.problems.append(f"{self.where}: .{node.attr} is not in APP_ATTRS or STDLIB_ATTRS")
        if node.attr == "executescript":
            if not self._allowed_script(node):
                self.problems.append(f"{self.where}: executescript is not allowed outside db.connect")
        elif node.attr in FORBIDDEN_ATTRS:
            self.problems.append(f"{self.where}: .{node.attr} hides what the code can run")
        if node.attr in EXECUTE_CALLS and id(node) not in self.called:
            self.problems.append(f"{self.where}: .{node.attr} is mentioned without being called here")
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in DB_METHODS | FORBIDDEN_ATTRS:
            self.problems.append(f"{self.where}: the text {node.value!r} names a database method")

    def visit_Import(self, node):
        for alias in node.names:
            self._check_module(alias.name)

    def visit_ImportFrom(self, node):
        name = node.module or ""
        self._check_module(name)
        if node.level == 0 and name.split(".")[0] != "app":
            for alias in node.names:
                if alias.name not in APP_ATTRS | STDLIB_ATTRS | {"dataclass"}:
                    self.problems.append(f"{self.where}: importing {alias.name} from {name} is not an allowed name")

    def _check_module(self, name):
        if name.split(".")[0] not in ALLOWED_MODULES | {"app", ""}:
            self.problems.append(f"{self.where}: importing {name} is not in ALLOWED_MODULES")

    def _allowed_script(self, node):
        return node.attr == "executescript" and self.module == "db" and self.stack[-1:] == ["connect"]

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Attribute):
            self.called.add(id(func))
        if isinstance(func, ast.Attribute) and func.attr in EXECUTE_CALLS:
            arg = node.args[0] if node.args else None
            if func.attr == "executescript":
                if not (isinstance(arg, ast.Name) and arg.id == "SCHEMA" and self._allowed_script(func)):
                    self.problems.append(f"{self.where}: executescript is allowed only as db.connect's SCHEMA")
            elif not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                self.problems.append(f"{self.where}: {func.attr} must be given a string literal")
            elif is_writing(arg.value):
                self.writers.add(self.where)
        self.generic_visit(node)


def module_name(path, root):
    rel = path.relative_to(root)
    return rel.parent.name if rel.name == "__init__.py" and rel.parent.name else rel.stem


def scan_sources(modules):
    """modules: {module name: source text}. Returns (functions that write, problems found)."""
    writers, problems = set(), []
    for name, source in sorted(modules.items()):
        scanner = _Scanner(name)
        scanner.visit(ast.parse(source))
        writers |= scanner.writers
        problems += scanner.problems
    return writers, problems


def scan_app(app_root):
    root = pathlib.Path(app_root)
    modules = {}
    for path in sorted(root.rglob("*.py")):
        name = module_name(path, root)
        if name in modules:
            raise AssertionError(f"two modules would be scanned as {name!r}; rename one")
        modules[name] = path.read_text(encoding="utf-8")
    return scan_sources(modules)
