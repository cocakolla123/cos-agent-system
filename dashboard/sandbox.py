#!/usr/bin/env python3
"""Run code the system did not write inside an OS sandbox (stdlib only).

Used for anything that executes a repository's own code, today the test
command ``/cos-fix`` runs after patching a repo (``codefix.run_tests``). That
code came from the repo and from a model, so it is treated as hostile:

- no network at all (no sockets, no DNS);
- file reads only inside the work tree, a fresh temp dir, and the system and
  toolchain paths an interpreter needs to start. The home directory, and the
  dashboard's ``connections.json``/``secrets.json``, ``~/.ssh`` and
  ``~/.claude.json`` with it, cannot be read;
- file writes only inside the work tree and the temp dir;
- a minimal environment: no tokens or keys, and ``HOME``/``TMPDIR`` pointing
  at the fresh temp dir;
- a hard timeout that kills the whole process group.

Backends: macOS ``sandbox-exec`` with a generated deny-by-default profile, and
Linux ``bwrap`` (bubblewrap) with only the allowed paths mounted. With neither,
``run`` raises ``SandboxUnavailable`` instead of running the code unsandboxed:
it fails closed.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile

# what the sandboxed process inherits from the caller's environment. Never
# keys or tokens; HOME and TMPDIR are replaced with the per-run temp dir.
ENV_KEEP = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "PYTHONPATH",
            "VIRTUAL_ENV", "JAVA_HOME", "GOROOT", "NODE_PATH")

# read-only system and toolchain roots, per platform (missing ones are skipped)
DARWIN_READ = (
    "/usr", "/bin", "/sbin", "/System", "/Library/Apple",
    "/Library/Developer", "/Library/Frameworks", "/Library/Java",
    "/Applications/Xcode.app", "/opt/homebrew", "/opt/local",
    "/private/etc", "/private/var/db/timezone", "/private/var/db/dyld",
    "/private/var/select", "/private/var/db/xcode_select_link", "/dev",
    # the /usr/bin shims (python3, git, ...) run xcrun, which checks the
    # Xcode license acceptance here
    "/Library/Preferences/com.apple.dt.Xcode.plist",
)
LINUX_READ = (
    "/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/etc",
    "/opt/hostedtoolcache",
)

DEFAULT_TIMEOUT = 900
SANDBOX_EXEC = "/usr/bin/sandbox-exec"


class SandboxUnavailable(RuntimeError):
    """No OS sandbox on this machine; the untrusted code was not run."""


class SandboxTimeout(RuntimeError):
    """The sandboxed command ran past its hard timeout and was killed."""


def backend():
    """'sandbox-exec', 'bwrap', or None when this machine has neither."""
    if sys.platform == "darwin" and os.access(SANDBOX_EXEC, os.X_OK):
        return "sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("bwrap"):
        return "bwrap"
    return None


def unavailable_message():
    if sys.platform == "darwin":
        how = "%s is missing" % SANDBOX_EXEC
    elif sys.platform.startswith("linux"):
        how = "install bubblewrap (apt install bubblewrap) so 'bwrap' is on PATH"
    else:
        how = "no supported sandbox on %s" % sys.platform
    return ("refusing to run untrusted code without a sandbox: %s. Nothing was run." % how)


def _real(p):
    return os.path.realpath(os.path.abspath(p))


def _home():
    return _real(os.path.expanduser("~"))


def _is_too_broad(path):
    """A read root that would expose the home directory (or everything)."""
    home = _home()
    return path in ("/", "/Users", "/home", "/private", "/private/var", "/var") or \
        path == home or home.startswith(path.rstrip("/") + "/")


def _interpreter_roots(argv0, env):
    """Install prefix of the program being run, so an interpreter living in the
    home directory (uv, pyenv, a venv) can still start. Only the prefix itself
    is exposed, never its parent."""
    roots = []
    exe = argv0 if os.sep in argv0 else shutil.which(argv0, path=env.get("PATH"))
    if not exe:
        return roots
    # the resolved install, not the symlink's directory (~/.local/bin would
    # expose ~/.local); following a symlink needs only metadata, allowed anyway
    d = os.path.dirname(_real(exe))
    prefix = os.path.dirname(d) if os.path.basename(d) == "bin" else d
    if os.path.dirname(prefix) == _home():
        # a prefix directly in the home dir (~/.cargo, ~/.bun, ~/go) also holds
        # that tool's credentials and caches: expose only its bin/
        prefix = d
    roots.append(prefix)
    if env.get("VIRTUAL_ENV"):
        roots.append(_real(env["VIRTUAL_ENV"]))
    return roots


def _read_roots(argv, env, extra_read):
    base = DARWIN_READ if sys.platform == "darwin" else LINUX_READ
    roots = []
    for p in list(base) + _interpreter_roots(argv[0], env) + list(extra_read or ()):
        p = _real(p) if os.path.exists(p) else None
        if not p or p in roots:
            continue
        if _is_too_broad(p):
            continue  # never widen to the home directory; the program may then fail to start
        roots.append(p)
    return roots


def _sb_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def darwin_profile(workdir, tmp, read_roots):
    """The sandbox-exec profile: deny everything, then allow only what a test
    run needs. Later rules win, and nothing below allows network."""
    rw = "\n".join("  (subpath %s)" % _sb_str(p) for p in (workdir, tmp))
    ro = "\n".join("  (subpath %s)" % _sb_str(p) for p in read_roots)
    return """(version 1)
(deny default)
(import "bsd.sb")
(allow process-fork)
(allow process-exec)
(allow signal (target same-sandbox))
(allow sysctl-read)
(allow ipc-posix-sem)
(allow ipc-posix-shm)
(allow file-read-metadata)
(allow file-read* file-test-existence
%s
%s)
(allow file-write*
%s
  (literal "/dev/null") (literal "/dev/zero") (literal "/dev/tty")
  (literal "/dev/stdout") (literal "/dev/stderr") (subpath "/dev/fd"))
(allow file-ioctl (literal "/dev/tty") (literal "/dev/null"))
(deny network*)
""" % (rw, ro, rw)


def _darwin_argv(argv, workdir, tmp, read_roots):
    return [SANDBOX_EXEC, "-p", darwin_profile(workdir, tmp, read_roots), "--", *argv]


def _bwrap_argv(argv, workdir, tmp, read_roots):
    cmd = [shutil.which("bwrap"), "--unshare-all", "--die-with-parent", "--new-session",
           "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for p in read_roots:  # real paths
        cmd += ["--ro-bind", p, p]
    # merged-/usr systems: /bin, /lib64 (the ELF loader's path) ... are
    # symlinks into /usr and must exist as such inside the sandbox
    for p in LINUX_READ:
        if os.path.islink(p):
            cmd += ["--symlink", os.readlink(p), p]
    cmd += ["--bind", tmp, tmp, "--bind", workdir, workdir, "--chdir", workdir, "--", *argv]
    return cmd


def _env(env, tmp):
    src = os.environ if env is None else env
    out = {k: v for k, v in src.items() if k in ENV_KEEP}
    out.setdefault("PATH", "/usr/bin:/bin")
    out.update(HOME=tmp, TMPDIR=tmp, TMP=tmp, TEMP=tmp, PYTHONDONTWRITEBYTECODE="1")
    if sys.platform == "darwin":
        # xcrun (behind /usr/bin/python3, git, ...) caches outside TMPDIR
        # unless told otherwise
        out["xcrun_db"] = os.path.join(tmp, "xcrun_db")
    return out


def run(argv, workdir, timeout=DEFAULT_TIMEOUT, extra_read=(), env=None):
    """Run ``argv`` in ``workdir`` inside the sandbox. Returns a
    ``subprocess.CompletedProcess`` with text stdout/stderr.

    ``extra_read`` adds read-only paths (never the home directory). ``env`` is
    the environment to filter (default: this process's). Raises
    ``SandboxUnavailable`` when there is no sandbox (nothing is run) and
    ``SandboxTimeout`` when the hard timeout kills the run."""
    argv = list(argv)
    if not argv:
        raise ValueError("empty command")
    kind = backend()
    if kind is None:
        raise SandboxUnavailable(unavailable_message())
    workdir = _real(workdir)
    if not os.path.isdir(workdir):
        raise ValueError("no such work tree: %s" % workdir)
    if _is_too_broad(workdir):
        raise ValueError("refusing a work tree that is or contains the home directory: %s" % workdir)
    tmp = _real(tempfile.mkdtemp(prefix="cos-sandbox-"))
    try:
        child_env = _env(env, tmp)
        roots = _read_roots(argv, child_env, extra_read)
        wrap = _darwin_argv if kind == "sandbox-exec" else _bwrap_argv
        proc = subprocess.Popen(wrap(argv, workdir, tmp, roots), cwd=workdir, env=child_env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            proc.communicate()
            raise SandboxTimeout("killed after %ss: %s" % (timeout, " ".join(argv)))
        finally:
            if proc.poll() is None:
                _kill_group(proc)
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


if __name__ == "__main__":
    # python3 sandbox.py <workdir> -- <command...>   (manual checks)
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        sys.exit("usage: sandbox.py <workdir> -- <command...>")
    try:
        r = run(sys.argv[3:], sys.argv[1])
    except (SandboxUnavailable, SandboxTimeout) as exc:
        sys.exit(str(exc))
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    sys.exit(r.returncode)
