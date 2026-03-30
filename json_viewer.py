import re
import tkinter as tk
from tkinter import ttk, messagebox
import json


def _decode_hex_escapes(text: str) -> str:
    """
    将文本中连续的 \\xHH 序列作为 UTF-8 字节解码为 Unicode 字符。
    例如：\\xE7\\xA8\\x8B\\xE5\\xBA\\x8F  →  程序
    解码失败的序列保留原样。
    """
    def replacer(m: re.Match) -> str:
        hex_parts = re.findall(r'[0-9A-Fa-f]{2}', m.group(0))
        raw = bytes(int(h, 16) for h in hex_parts)
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError:
            return m.group(0)           # 无法解码则保留原始文本

    return re.sub(r'(?:\\x[0-9A-Fa-f]{2})+', replacer, text)


def prepare_text(raw_text: str) -> str:
    """
    执行所有文本转换，返回待解析的纯 JSON 字符串（不调用 json.loads）。
    步骤：
      1. 找第一个 \" → start = 其左边一个字符
      2. 找最后一个 \" 之后的第一个 " → end（含，即 JSON 字符串的闭合引号；无则取末尾）
      3. 截取 → 清除换行 → \" 反转义 → 去首尾引号
    """
    first_esc = raw_text.find('\\"')
    if first_esc == -1:
        return raw_text.strip()

    start = max(0, first_esc - 1)

    last_esc = raw_text.rfind('\\"')
    after_last = last_esc + 2          # 跳过 \" 本身
    quote_pos = raw_text.find('"', after_last)
    # 找到闭合引号则截取到它（含），否则取到末尾
    end = quote_pos + 1 if quote_pos != -1 else len(raw_text)

    text = raw_text[start:end]
    text = text.replace('\r\n', '').replace('\n', '').replace('\r', '')
    text = text.replace('\\"', '"')
    text = _decode_hex_escapes(text)   # \xHH → UTF-8 字符
    text = text.strip()
    if text.startswith('"'):
        text = text[1:0]
    if text.endswith('"'):
        text = text[:-1]

    return text


def process_input(raw_text: str):
    """预处理后直接解析为 JSON 对象。"""
    return json.loads(prepare_text(raw_text))


class JsonViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JSON Log Viewer")
        self.root.geometry("960x700")
        self.root.minsize(600, 400)

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # ── 输入区 ──────────────────────────────────────────────────────
        input_frame = ttk.LabelFrame(self.root, text="输入（粘贴日志内容）", padding=6)
        input_frame.pack(fill=tk.X, padx=10, pady=(8, 0))

        self.input_text = tk.Text(
            input_frame, height=9, wrap=tk.NONE, font=("Consolas", 10),
            undo=True, relief=tk.SUNKEN, borderwidth=1
        )
        in_xsb = ttk.Scrollbar(input_frame, orient=tk.HORIZONTAL,
                                command=self.input_text.xview)
        in_ysb = ttk.Scrollbar(input_frame, orient=tk.VERTICAL,
                                command=self.input_text.yview)
        self.input_text.configure(xscrollcommand=in_xsb.set,
                                  yscrollcommand=in_ysb.set)

        in_ysb.pack(side=tk.RIGHT, fill=tk.Y)
        in_xsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # ── 按钮区 ──────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Button(btn_frame, text="▶  解析 JSON",
                   command=self.parse_json).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="清空",
                   command=self.clear_all).pack(side=tk.LEFT, padx=6)
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(btn_frame, text="全部展开",
                   command=self.expand_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="全部收起",
                   command=self.collapse_all).pack(side=tk.LEFT, padx=6)

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(btn_frame, textvariable=self.status_var,
                  foreground="gray").pack(side=tk.RIGHT, padx=4)

        # ── 树视图区 ────────────────────────────────────────────────────
        tree_frame = ttk.LabelFrame(self.root, text="JSON 结构", padding=6)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "value"),
            show="tree headings",
            selectmode="browse"
        )
        self.tree.heading("#0",     text="键 / 索引")
        self.tree.heading("type",   text="类型")
        self.tree.heading("value",  text="值")
        self.tree.column("#0",    width=260, minwidth=120, stretch=True)
        self.tree.column("type",  width=80,  minwidth=60,  stretch=False, anchor=tk.CENTER)
        self.tree.column("value", width=560, minwidth=120, stretch=True)

        t_vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                               command=self.tree.yview)
        t_hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                               command=self.tree.xview)
        self.tree.configure(yscrollcommand=t_vsb.set,
                            xscrollcommand=t_hsb.set)

        t_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        t_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 双击节点复制值到剪贴板
        self.tree.bind("<Double-1>", self._on_double_click)

        # 绑定 Ctrl+V 快捷键直接解析
        self.root.bind("<Control-Return>", lambda _: self.parse_json())

    # ------------------------------------------------------------------ #
    #  核心逻辑
    # ------------------------------------------------------------------ #
    def parse_json(self):
        raw = self.input_text.get("1.0", tk.END)
        if not raw.strip():
            self.status_var.set("⚠ 输入为空")
            return
        processed = None
        try:
            processed = prepare_text(raw)
            data = json.loads(processed)
            self.tree.delete(*self.tree.get_children())
            self._populate("", None, data)
            total = self._count_nodes()
            self.status_var.set(f"✔ 解析成功，共 {total} 个节点")
        except json.JSONDecodeError as e:
            self.status_var.set("✘ JSON 解析失败")
            self._show_json_error(e, processed)
        except Exception as e:
            self.status_var.set("✘ 错误")
            messagebox.showerror("错误", str(e))

    def _show_json_error(self, e: json.JSONDecodeError, text: str | None):
        """弹出窗口，显示处理后的 JSON 文本并在出错位置插入红色标记。"""
        win = tk.Toplevel(self.root)
        win.title("JSON 解析失败")
        win.geometry("860x520")
        win.resizable(True, True)

        # ── 错误描述 ──────────────────────────────────────────────────
        ttk.Label(
            win,
            text=f"错误：{e.msg}   （行 {e.lineno}，列 {e.colno}，字符位置 {e.pos}）",
            foreground="red",
            wraplength=820,
            font=("", 10, "bold")
        ).pack(padx=10, pady=(10, 4), anchor="w")

        # ── 处理后文本（带错误标记）──────────────────────────────────
        if text is not None:
            frame = ttk.LabelFrame(win, text="处理后的 JSON 文本", padding=4)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

            txt = tk.Text(frame, font=("Consolas", 10), wrap=tk.NONE)
            xsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=txt.xview)
            ysb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=txt.yview)
            txt.configure(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
            ysb.pack(side=tk.RIGHT,  fill=tk.Y)
            xsb.pack(side=tk.BOTTOM, fill=tk.X)
            txt.pack(fill=tk.BOTH, expand=True)

            pos = e.pos if e.pos is not None else len(text)
            txt.insert("end", text[:pos])
            txt.insert("end", "◄ERR►", "error_mark")
            txt.insert("end", text[pos:])

            txt.tag_configure("error_mark",
                              foreground="white", background="red",
                              font=("Consolas", 10, "bold"))

            # 跳转到出错位置
            err_idx = f"1.{pos}"
            txt.see(err_idx)
            txt.configure(state=tk.DISABLED)

        # ── 关闭按钮 ──────────────────────────────────────────────────
        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=8)

    def _populate(self, parent: str, key, value):
        """递归向 Treeview 插入节点。"""
        label = str(key) if key is not None else ""

        if isinstance(value, dict):
            node = self.tree.insert(
                parent, "end",
                text=label,
                values=("object", f"{{ {len(value)} 个键 }}"),
                open=True
            )
            for k, v in value.items():
                self._populate(node, k, v)

        elif isinstance(value, list):
            node = self.tree.insert(
                parent, "end",
                text=label,
                values=("array", f"[ {len(value)} 个元素 ]"),
                open=True
            )
            for i, v in enumerate(value):
                self._populate(node, f"[{i}]", v)

        else:
            type_name = type(value).__name__   # str / int / float / bool / NoneType
            if isinstance(value, bool):
                type_name = "bool"
                display = "true" if value else "false"
            elif value is None:
                type_name = "null"
                display = "null"
            elif isinstance(value, str):
                type_name = "string"
                display = value                 # 直接显示原始字符串内容
            else:
                type_name = "number"
                display = str(value)

            self.tree.insert(
                parent, "end",
                text=label,
                values=(type_name, display)
            )

    # ------------------------------------------------------------------ #
    #  辅助操作
    # ------------------------------------------------------------------ #
    def _walk(self, item=""):
        yield item
        for child in self.tree.get_children(item):
            yield from self._walk(child)

    def _count_nodes(self):
        return sum(1 for _ in self._walk()) - 1   # 去掉虚根

    def expand_all(self):
        for item in self._walk():
            self.tree.item(item, open=True)

    def collapse_all(self):
        for item in self.tree.get_children():   # 只收起顶层，子项跟随
            self._set_open(item, False)

    def _set_open(self, item, state: bool):
        self.tree.item(item, open=state)
        for child in self.tree.get_children(item):
            self._set_open(child, state)

    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("就绪")

    def _on_double_click(self, event):
        """双击叶节点时，将其值复制到系统剪贴板。"""
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item, "values")
        if values and len(values) >= 2:
            val = values[1]
            self.root.clipboard_clear()
            self.root.clipboard_append(val)
            self.status_var.set(f"已复制：{val[:60]}{'…' if len(val) > 60 else ''}")


# ------------------------------------------------------------------ #
#  入口
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    root = tk.Tk()
    # 在 Windows 上启用高 DPI 支持
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = JsonViewerApp(root)
    root.mainloop()

