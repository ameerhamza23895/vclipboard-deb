#!/usr/bin/env python3
"""
V Clipboard - Windows-style clipboard history for Linux.
Press Super+V (Windows key + V) anywhere to open clipboard history.
"""
import sys
import os
import time
import threading
import fcntl
from PyQt5.QtWidgets import (
    QApplication, QWidget, QListWidget, QListWidgetItem,
    QVBoxLayout, QSystemTrayIcon, QMenu, QAction, QStyledItemDelegate,
    QStyleOptionViewItem
)
from PyQt5.QtGui import QIcon, QCursor, QFontMetrics
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

try:
    from pynput import keyboard
    from pynput.keyboard import Key
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard = None
    Key = None

HISTORY_FILE = os.path.expanduser("~/.vclipboard_history.txt")
MAX_HISTORY_ITEMS = 50
MAX_HISTORY_FILE_LINES = 100


class MultiLineItemDelegate(QStyledItemDelegate):
    """Show multi-line clipboard entries with enough row height."""
    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ""
        line_count = max(1, text.count("\n") + 1)
        lines_to_show = min(max(2, line_count), 8)
        fm = QFontMetrics(option.font)
        w = option.rect.width() - 10 if option.rect.width() > 0 else 400
        if w <= 0:
            w = 400
        try:
            br = fm.boundingRect(0, 0, w, 0, Qt.TextWordWrap, text)
            h = max(br.height(), fm.lineSpacing() * lines_to_show)
        except Exception:
            h = fm.lineSpacing() * lines_to_show
        return QSize(option.rect.width() if option.rect.width() > 0 else 450, max(36, h + 8))


class ClipboardWindow(QWidget):
    show_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("V Clipboard")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.resize(450, 350)

        self.list_widget = QListWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(2)
        self.list_widget.setItemDelegate(MultiLineItemDelegate(self.list_widget))
        self.list_widget.setTextElideMode(Qt.ElideNone)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_list_context_menu)

        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.save_clipboard)

        self.list_widget.itemActivated.connect(self.paste_selected)
        self.list_widget.itemClicked.connect(self.paste_selected)
        self.show_requested.connect(self.show_at_cursor)

        self.load_history()

    def save_clipboard(self):
        text = self.clipboard.text()
        if not text or not text.strip():
            return

        if self.list_widget.count() == 0 or self.list_widget.item(0).text() != text:
            self.list_widget.insertItem(0, text)
            while self.list_widget.count() > MAX_HISTORY_ITEMS:
                self.list_widget.takeItem(self.list_widget.count() - 1)
            self._write_history_file()

    def _write_history_file(self):
        lines = []
        for i in range(min(self.list_widget.count(), MAX_HISTORY_FILE_LINES)):
            lines.append(self.list_widget.item(i).text().replace("\n", "\\n"))
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            seen = set()
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.replace("\\n", "\n").strip()
                    if line and line not in seen:
                        seen.add(line)
                        self.list_widget.addItem(line)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def clear_all(self):
        self.list_widget.clear()
        self._write_history_file()

    def delete_item(self, item=None):
        if item is None:
            item = self.list_widget.currentItem()
        if not item:
            return
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self._write_history_file()

    def show_list_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        menu = QMenu(self)
        delete_action = None
        if item is not None:
            delete_action = menu.addAction("Delete")
        clear_action = menu.addAction("Clear all")
        action = menu.exec_(self.list_widget.viewport().mapToGlobal(pos))
        if action is None:
            return
        if action == delete_action and item is not None:
            self.delete_item(item)
        elif action == clear_action:
            self.clear_all()

    def show_at_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() - 200, pos.y() - 100)
        self.show()
        self.raise_()
        self.activateWindow()
        self.list_widget.setFocus()
        self.list_widget.setCurrentRow(0)

    def paste_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        text = item.text()
        self.clipboard.setText(text)
        self.hide()

        # Send Ctrl+V after a short delay so the previous window gets focus and clipboard is ready
        def send_paste():
            if not PYNPUT_AVAILABLE:
                return
            try:
                kb = keyboard.Controller()
                kb.press(keyboard.Key.ctrl)
                kb.press("v")
                kb.release("v")
                kb.release(keyboard.Key.ctrl)
            except Exception:
                pass

        QTimer.singleShot(200, send_paste)

def _is_v_key(key):
    try:
        return hasattr(key, "char") and key.char and key.char.lower() == "v"
    except Exception:
        return False


def _is_super_key(key):
    """Detect Super/Windows key (pynput reports it differently on some Linux setups)."""
    if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        return True
    try:
        s = str(key).lower()
        return "cmd" in s or "super" in s or "win" in s
    except Exception:
        return False


def start_hotkey_listener(window):
    if not PYNPUT_AVAILABLE:
        return
    pressed = set()
    last_trigger = 0.0
    debounce_sec = 0.4

    def _alt_held():
        return Key.alt in pressed or Key.alt_l in pressed or Key.alt_r in pressed

    def on_press(key):
        nonlocal last_trigger
        try:
            pressed.add(key)
            super_held = _is_super_key(key) or any(_is_super_key(k) for k in pressed)
            v_held = _is_v_key(key) or any(_is_v_key(k) for k in pressed)
            ctrl_held = Key.ctrl in pressed or Key.ctrl_l in pressed or Key.ctrl_r in pressed
            alt_held = _alt_held()
            # Only two shortcuts: Win+V and Ctrl+Alt+V
            combo = (super_held and v_held) or (ctrl_held and alt_held and v_held)
            if combo and (time.time() - last_trigger) > debounce_sec:
                last_trigger = time.time()
                window.show_requested.emit()
        except Exception:
            pass

    def on_release(key):
        try:
            pressed.discard(key)
        except Exception:
            pass

    print("vclipboard: hotkey listener started (Win+V or Ctrl+Alt+V)", file=sys.stderr)
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    listener.join()

SINGLE_INSTANCE_NAME = "vclipboard-%s" % (os.getuid(),)
LOCK_FILE = "/tmp/vclipboard-%s.lock" % (os.getuid(),)


def try_show_existing_and_exit():
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_NAME)
    if sock.waitForConnected(800):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.close()
        return True
    return False


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    lock_fd = None
    try:
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except Exception:
                pass
            lock_fd = None
        app = QApplication(sys.argv)
        for _ in range(5):
            time.sleep(0.3)
            if try_show_existing_and_exit():
                sys.exit(0)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    server = QLocalServer()
    if not server.listen(SINGLE_INSTANCE_NAME):
        server.removeServer(SINGLE_INSTANCE_NAME)
        if not server.listen(SINGLE_INSTANCE_NAME):
            if try_show_existing_and_exit():
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except Exception:
                    pass
                sys.exit(0)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception:
                pass
            sys.exit(1)

    window = ClipboardWindow()
    if server.isListening():
        def on_new_connection():
            conn = server.nextPendingConnection()
            if conn and conn.bytesAvailable():
                conn.readAll()
            if conn:
                conn.close()
            window.show_requested.emit()
        server.newConnection.connect(on_new_connection)

    tray = QSystemTrayIcon(QIcon.fromTheme("edit-paste"))
    tray_tip = "V Clipboard (Win+V or Ctrl+Alt+V)" if PYNPUT_AVAILABLE else "V Clipboard (open from tray)"
    tray.setToolTip(tray_tip)

    menu = QMenu()
    menu.addAction(QAction("Show", triggered=window.show_at_cursor))
    menu.addAction(QAction("Exit", triggered=app.quit))
    tray.setContextMenu(menu)
    tray.show()

    if PYNPUT_AVAILABLE:
        threading.Thread(target=start_hotkey_listener, args=(window,), daemon=True).start()
    else:
        print("vclipboard: install pynput for Super+V hotkey: pip3 install pynput", file=sys.stderr)

    sys.exit(app.exec_())
