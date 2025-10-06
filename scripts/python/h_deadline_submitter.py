# -*- coding: utf-8 -*-
"""
Multi-engine Deadline submitter for Houdini with a PySide2 UI.

- Supports: Mantra ROP, Arnold ROP, USD Render (Karma & Arnold in Solaris),
  File Cache SOP, File Cache LOP (best-effort), and anything that looks similar.
- Uses a profile map per node type to determine:
    * which subnode is actually submitted (e.g. <node>/render),
    * how to read frames,
    * where to fetch output paths (self parms, upstream settings).

Python 3.7+ compatible. Functions use Google-style docstrings.
"""

import os
import re
import tempfile
import subprocess
from collections import OrderedDict

import hou
from PySide2 import QtCore, QtWidgets


# ───────────────────────────── Profiles (edit here) ───────────────────────── #

# Notes:
# - Keys are Houdini *type names* (lowercase). Use a set for aliases or versions.
# - submit_path: either "self" OR a list of candidate format strings, e.g. "{node}/render".
#   The first that exists will be used; falls back to node.path() if none exist.
# - output_parms: parameters (in order) that may contain the final output path on
#   this node or its upstream settings. We also scan upstream for these names.
# - frames: strategy name. "standard" reads trange,f1,f2,f3. You can add custom.
NODE_PROFILES = {
    # Mantra ROP
    "ifd": {
        "aliases": {"ifd",},
        "submit_path": "self",
        "output_parms": ["vm_picture"],
        "frames": "standard",
    },

    # Arnold ROP
    "arnold": {
        "aliases": {"arnold"},
        "submit_path": "self",
        "output_parms": ["ar_picture"],
        "frames": "standard",
    },

    # USD Render ROP (Solaris) — Karma, Arnold, etc.
    "usdrender_rop": {
        "aliases": {"usdrender_rop"},
        "submit_path": "self",
        "output_parms": ["outputimage"],
        "frames": "standard",
        # Some shots use upstream Karma/Arnold Render Settings; we’ll also scan upstream.
    },

    # File Cache SOP (/obj/…/filecache1) — submits the inner "render" node
    "filecache": {
        "aliases": {"filecache"},
        "submit_path": ["{node}/render"],
        "output_parms": ["sopoutput"],
        "frames": "standard",
    },

    # File Cache LOP (/obj/…/filecache1) — submits the inner "render" node
    "filecache_lop": {
        "aliases": {"filecache",},
        "submit_path": ["{node}/render"],
        "output_parms": ["lopoutput", "filepath", "outputimage", "picture"],
        "frames": "standard",
    },

    "axeflipio": {
        "aliases": {"axeflipio",},
        "submit_path": ["{node}/cache_none/render"],
        "output_parms": ["sopoutput"],
        "frames": "standard",
    },

    "axefx_file_cache": {
        "aliases": {"axefx_file_cache",},
        "submit_path": ["{node}/render"],
        "output_parms": ["sopoutput"],
        "frames": "standard",
    },

    # Generic fallback: any Driver/Lop with the common parms & standard frames.
    "_generic": {
        "aliases": set(),
        "submit_path": "self",
        "output_parms": ["filename", "file", "sopoutput", "lopoutput"],
        "frames": "standard",
    },
}


# ───────────────────────────── Helper functions ───────────────────────────── #

def find_deadline_command() -> str:
    """Find Deadline's 'deadlinecommand' executable.

    Returns:
        str: Absolute path to 'deadlinecommand'.

    Raises:
        FileNotFoundError: If the executable cannot be found.
    """
    env_path = os.environ.get("DEADLINE_PATH")

    if env_path:
        return os.path.join(env_path, "deadlinecommand.exe").replace('\\', '/')

    raise FileNotFoundError("Could not locate 'deadlinecommand'. Set DEADLINE_PATH or add it to PATH.")


def expand(path: str, sample_frame: int) -> str:
    """Expand Houdini variables and $F tokens to a concrete path.

    Args:
        path (str): Raw Houdini-style path with tokens.
        sample_frame (int): Frame for $F tokens.

    Returns:
        str: Expanded path.
    """
    if not path:
        return ""

    def repl(match):
        pad = match.group(1)
        if pad:
            return str(sample_frame).zfill(int(pad))
        return str(sample_frame)

    s = re.sub(r"\$F(\d+)?", repl, path)
    try:
        return hou.expandString(s)
    except Exception:
        return os.path.expandvars(s)


def node_parm(node: hou.Node, name: str, default=None):
    """Safely evaluate a parm on a node."""
    p = node.parm(name)
    if not p:
        return default
    try:
        return p.eval()
    except Exception:
        return default


def detect_frame_range_standard(node: hou.Node) -> (int, int, int):
    """Read frames via trange/f1/f2/f3 with sane fallbacks.

    Args:
        node: Node.

    Returns:
        (int, int, int): start, end, step.
    """
    trange = int(node_parm(node, "trange", 1))
    f1 = int(round(node_parm(node, "f1", int(hou.playbar.frameRange()[0]))))
    f2 = int(round(node_parm(node, "f2", int(hou.playbar.frameRange()[1]))))
    f3 = int(round(node_parm(node, "f3", 1)))

    if trange == 0:
        cur = int(round(hou.frame()))
        return cur, cur, 1

    if f3 <= 0:
        f3 = 1
    if f2 < f1:
        f1, f2 = f2, f1
    return f1, f2, f3


def frames_to_deadline_string(start: int, end: int, step: int) -> str:
    """Convert numeric range to Deadline 'Frames' string."""
    if start == end:
        return f"{start}"
    if step == 1:
        return f"{start}-{end}"
    return f"{start}-{end}x{step}"


def iter_upstream(node: hou.Node):
    """Breadth-first upstream iterator (unique nodes)."""
    seen = set()
    q = list(node.inputs() or [])
    while q:
        n = q.pop(0)
        if not n or n in seen:
            continue
        seen.add(n)
        yield n
        q.extend(list(n.inputs() or []))


def resolve_profile(node: hou.Node) -> dict:
    """Pick a NODE_PROFILES entry for this node by type name.

    Args:
        node: Node.

    Returns:
        dict: Profile (never None; falls back to _generic).
    """
    node_type = node.type().nameComponents()[2].lower()
    for key, prof in NODE_PROFILES.items():
        if key == "_generic":
            continue
        aliases = prof.get("aliases", {key})
        if node_type in aliases:
            return prof
    return NODE_PROFILES["_generic"]


def find_submit_path(node: hou.Node, profile: dict) -> str:
    """Compute the actual node path to submit (e.g., '<node>/render').

    Args:
        node: Selected node.
        profile: Profile dict.

    Returns:
        str: Existing node path suitable for 'ROPPath'.
    """
    submit = profile.get("submit_path", "self")
    if submit == "self":
        return node.path()

    if isinstance(submit, (list, tuple)):
        for pat in submit:
            candidate = pat.format(node=node.path())

            if hou.node(candidate):
                return candidate
        # last resort: self
        return node.path()

    # string pattern
    candidate = submit.format(node=node.path())
    return candidate


def find_output_path(node: hou.Node, start_frame: int, profile: dict) -> (str, str):
    """Find output directory and filename for Deadline outputs.

    Strategy:
      1) Check this node's parms using profile['output_parms'] (first match wins).
      2) Scan upstream nodes; if any have a parm with those names, use it.
      3) Special-case: for USD Render, also look for upstream Render Settings
         (Karma/Arnold/etc.) by finding any node whose parms include a hit.

    Args:
        node: Node being submitted.
        start_frame: Frame used to expand $F tokens.
        profile: Profile dict.

    Returns:
        (str, str): (odir, ofile) — may be empty strings.
    """
    names = profile.get("output_parms") or NODE_PROFILES["_generic"]["output_parms"]

    # 1) Direct on node
    for pname in names:
        raw = node_parm(node, pname, "")
        if raw:
            expd = expand(str(raw), start_frame)
            return os.path.dirname(expd), os.path.basename(expd)

    # 2) Upstream search
    for up in iter_upstream(node):
        for pname in names:
            raw = node_parm(up, pname, "")
            if raw:
                expd = expand(str(raw), start_frame)
                return os.path.dirname(expd), os.path.basename(expd)

    # Nothing found
    return "", ""


def detect_frames(node: hou.Node, profile: dict) -> (int, int, int):
    """Dispatch to the proper frame detection strategy."""
    mode = profile.get("frames", "standard")
    if mode == "standard":
        return detect_frame_range_standard(node)
    # Add custom strategies here if needed.
    return detect_frame_range_standard(node)


def build_job_info(node: hou.Node, name: str, frames: str, odir: str, ofile: str,
                   pool: str, group: str, priority: int) -> OrderedDict:
    """Build Deadline Job Info dict."""
    info = OrderedDict()
    info["Plugin"] = "Houdini"
    info["Name"] = name
    info["Comment"] = "Submitted via multi-engine Houdini tool."
    info["Department"] = ""
    info["Pool"] = pool or ""
    info["Group"] = group or ""
    info["Priority"] = str(int(priority))
    info["Frames"] = frames
    info["BatchName"] = hou.hipFile.basename()
    info["MachineLimit"] = "0"
    info["ConcurrentTasks"] = "1"
    info["ChunkSize"] = "1"
    if odir:
        info["OutputDirectory0"] = odir
    if ofile:
        info["OutputFilename0"] = ofile
    return info


def build_plugin_info(rop_path: str) -> OrderedDict:
    """Build Deadline Plugin Info dict for the Houdini plugin.

    Args:
        rop_path (str): Full path to the actual node/child to render.

    Returns:
        OrderedDict: Plugin info.
    """
    hmaj, hmin, hbuild = hou.applicationVersion()
    hip = hou.hipFile.path()

    plug = OrderedDict()
    plug["SceneFile"] = hip
    plug["Version"] = f"{hmaj}.{hmin}.{hbuild}"
    plug["Build"] = "64bit"
    plug["IgnoreInputs"] = "0"
    plug["OutputDriver"] = rop_path
    # Optional: Use Hython instead of hbatch if your farm requires
    # plug["UseHython"] = "true"
    return plug


def write_kv(path: str, data: OrderedDict) -> None:
    """Write a simple key=value file for Deadline."""
    with open(path, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")


def submit_to_deadline(job_info: OrderedDict, plugin_info: OrderedDict, dl_cmd: str) -> (int, str):
    """Submit a single job to Deadline using deadlinecommand."""
    tmpdir = tempfile.mkdtemp(prefix="dl_hou_")
    job_path = os.path.join(tmpdir, "job_info.job")
    plugin_path = os.path.join(tmpdir, "plugin_info.job")
    write_kv(job_path, job_info)
    write_kv(plugin_path, plugin_info)

    proc = subprocess.Popen([dl_cmd, job_path, plugin_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True)
    out, _ = proc.communicate()
    return proc.returncode, out


def derive_job_name(node: hou.Node) -> str:
    """Prefer custom parms like 'jobname'/'job_name', else HIP + node name."""
    jobname = node_parm(node, "jobname") or node_parm(node, "job_name")
    if jobname:
        return str(jobname)
    return f"{os.path.splitext(hou.hipFile.basename())[0]}_{node.name()}"


def collect_selected_nodes() -> list:
    """Collect selected nodes that we can submit (Driver/SOP/LOP), keep order."""
    picked = []
    for n in hou.selectedNodes() or []:
        # Filter to common categories, but allow everything (profile may still resolve).
        cat = n.type().category().name()
        if cat in {"Driver", "Sop", "Lop"}:
            picked.append(n)
    return picked


# ─────────────────────────────────── UI ──────────────────────────────────── #

class DeadlineSubmitterUI(QtWidgets.QDialog):
    """Simple UI to submit selected nodes to Deadline (multi-engine)."""

    def __init__(self, parent=None):
        super(DeadlineSubmitterUI, self).__init__(parent)
        self.setWindowTitle("Submit to Deadline (Multi-Engine)")
        self.setMinimumWidth(820)
        self.nodes = collect_selected_nodes()

        self._build_ui()
        self._populate_table()

    def _build_ui(self) -> None:
        """Create widgets and layout."""
        vbox = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Node", "Type", "Submit Path", "Job Name", "Frames", "Output Dir", "Output File"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        vbox.addWidget(self.table)

        opts = QtWidgets.QHBoxLayout()
        self.pool = QtWidgets.QLineEdit(self); self.pool.setPlaceholderText("Pool (optional)")
        self.group = QtWidgets.QLineEdit(self); self.group.setPlaceholderText("Group (optional)")
        self.priority = QtWidgets.QSpinBox(self); self.priority.setRange(0, 100); self.priority.setValue(50)
        self.refresh_btn = QtWidgets.QPushButton("Refresh Selection", self)
        opts.addWidget(self.pool)
        opts.addWidget(self.group)
        opts.addWidget(QtWidgets.QLabel("Priority:", self))
        opts.addWidget(self.priority)
        opts.addStretch(1)
        opts.addWidget(self.refresh_btn)
        vbox.addLayout(opts)

        btns = QtWidgets.QHBoxLayout()
        self.submit_btn = QtWidgets.QPushButton("Submit to Deadline", self)
        self.close_btn = QtWidgets.QPushButton("Close", self)
        btns.addStretch(1)
        btns.addWidget(self.submit_btn)
        btns.addWidget(self.close_btn)
        vbox.addLayout(btns)

        self.refresh_btn.clicked.connect(self._on_refresh)
        self.close_btn.clicked.connect(self.reject)
        self.submit_btn.clicked.connect(self._on_submit)

    def _populate_table(self) -> None:
        """Fill the table with selected node info."""
        self.table.setRowCount(0)

        rows = []
        for node in self.nodes:
            prof = resolve_profile(node)
            submit_path = find_submit_path(node, prof)
            frame_start, frame_end, frame_interval = detect_frames(node, prof)
            frames = frames_to_deadline_string(frame_start, frame_end, frame_interval)
            odir, ofile = find_output_path(node, frame_start, prof)
            rows.append((node, node.type().name(), submit_path, derive_job_name(node), frames, odir, ofile))

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                # Pretty: show node path for 1st col (node object)
                if c == 0:
                    val = row[0].path()
                item = QtWidgets.QTableWidgetItem(str(val))
                item.setToolTip(str(val))
                self.table.setItem(r, c, item)

        self.table.resizeColumnsToContents()

    # Actions
    def _on_refresh(self) -> None:
        self.nodes = collect_selected_nodes()
        if not self.nodes:
            QtWidgets.QMessageBox.information(self, "No Nodes Selected",
                                              "Select one or more nodes (Driver/SOP/LOP) and click Refresh.")
        self._populate_table()

    def _on_submit(self) -> None:
        if not self.nodes:
            QtWidgets.QMessageBox.warning(self, "Nothing to submit", "No nodes selected.")
            return

        try:
            dl_cmd = find_deadline_command()
        except FileNotFoundError as e:
            QtWidgets.QMessageBox.critical(self, "Deadline Not Found", str(e))
            return

        pool = self.pool.text().strip()
        group = self.group.text().strip()
        priority = int(self.priority.value())

        logs = []
        for n in self.nodes:
            prof = resolve_profile(n)
            rop_path = find_submit_path(n, prof)
            s, e, st = detect_frames(n, prof)
            frames = frames_to_deadline_string(s, e, st)
            odir, ofile = find_output_path(n, s, prof)

            job_info = build_job_info(n, derive_job_name(n), frames, odir, ofile, pool, group, priority)
            plugin_info = build_plugin_info(rop_path)
            rc, out = submit_to_deadline(job_info, plugin_info, dl_cmd)

            tag = "SUCCESS" if rc == 0 else "ERROR"
            logs.append(f"[{tag}] {n.path()}  ->  {rop_path}\n{out.strip()}\n")

        QtWidgets.QMessageBox.information(self, "Submission Results", "\n\n".join(logs))

        # Optional: save HIP after submission
        try:
            hou.hipFile.save()
        except Exception:
            pass


# ───────────────────────────────── Runner ────────────────────────────────── #

def show_deadline_submitter() -> None:
    """
    Create and show the Deadline submitter dialog.
    """
    dlg = DeadlineSubmitterUI(hou.ui.mainQtWindow())
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()




