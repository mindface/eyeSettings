import tkinter as tk
import tkinter.font as tkFont
from tkinter import colorchooser, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageTk, ImageFont
import copy

class Layer:
    def __init__(self, w, h):
        # RGBA レイヤー（透明背景）
        self.image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

class Editor:
    def __init__(self, root):
        self.root = root
        self.root.title("多機能画像エディタ（すべて PIL に描画）")

        self.w, self.h = 1500, 650

        # --- グリッド設定 ---
        self.grid_size = 20
        self.use_grid = True

        # ---- レイヤー管理 ----
        self.layers = [Layer(self.w, self.h)]
        self.active_layer = 0

        # ---- Undo / Redo ----
        self.undo_stack = []
        self.redo_stack = []

        # ---- モード管理 ----
        self.mode = "draw"      # draw / erase / rect / oval / text / select
        self.color = "black"
        self.fill_color = None  # None = no fill / "" でも可
        self.brush_size = 5

        # ---- 表示（ズーム / オフセット）----
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # ---- Canvas ----
        self.canvas = tk.Canvas(root, bg="gray", width=self.w, height=self.h)
        self.canvas.pack(fill="both", expand=True)

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.zoom_event)       # Windows
        self.canvas.bind("<Button-4>", self.zoom_event)        # Linux scroll up (optional)
        self.canvas.bind("<Button-5>", self.zoom_event)        # Linux scroll down (optional)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)    # middle button
        self.canvas.bind("<B2-Motion>", self.pan_move)

        # ---- 一時変数 ----
        self.start_x = None
        self.start_y = None
        self.temp_shape = None   # Canvas 上のプレビュー図形（矩形／楕円）
        self.selected_item = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # ---- フォント設定 ----
        self.font_size = 20
        self.font_family = "Yu Gothic"  # 日本語対応の代表的フォント

        self.text_font = ImageFont.truetype(
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            self.font_size
        )
        # UI
        self.create_ui()

        # 最初の表示
        self.update_canvas()

    # ---------------- ユーティリティ ----------------
    def snap(self, v):
        if not self.use_grid or self.grid_size <= 0:
            return v
        return round(v / self.grid_size) * self.grid_size

    def screen_to_canvas(self, sx, sy):
        """スクリーン系（イベント座標） -> キャンバス（画像）座標（未ズーム）"""
        return int((sx - self.offset_x) / self.zoom), int((sy - self.offset_y) / self.zoom)

    def canvas_to_screen(self, cx, cy):
        """キャンバス（画像）座標 -> スクリーン系（キャンバス上の表示ピクセル）"""
        return int(cx * self.zoom + self.offset_x), int(cy * self.zoom + self.offset_y)

    # ---------------- UI ----------------
    def create_ui(self):
        frame = tk.Frame(self.root)
        frame.pack(anchor="nw", padx=4, pady=4)

        tk.Button(frame, text="🖊 描画", command=lambda: self.set_mode("draw")).pack(side="left")
        tk.Button(frame, text="🧽 消しゴム", command=lambda: self.set_mode("erase")).pack(side="left")
        tk.Button(frame, text="▭ 四角形", command=lambda: self.set_mode("rect")).pack(side="left")
        tk.Button(frame, text="◯ 丸", command=lambda: self.set_mode("oval")).pack(side="left")
        tk.Button(frame, text="🔤 テキスト", command=lambda: self.set_mode("text")).pack(side="left")
        tk.Button(frame, text="選択(移動不可)", command=lambda: self.set_mode("select")).pack(side="left")  # 選択は有効だが編集は不可（方式A）
        tk.Button(frame, text="🎨 色", command=self.choose_color).pack(side="left")
        tk.Button(frame, text="塗りつぶし色", command=self.choose_fill).pack(side="left")
        tk.Button(frame, text="📷 画像読み込み", command=self.load_image_to_layer).pack(side="left")

        # 文字サイズ
        self.font_var = tk.IntVar(value=20)
        tk.Spinbox(frame, from_=8, to=200, textvariable=self.font_var,
                command=self.change_font_size, width=5).pack(side="left")

        # ブラシサイズ
        self.brush_var = tk.IntVar(value=self.brush_size)
        tk.Spinbox(frame, from_=1, to=100, textvariable=self.brush_var,
                   command=self.change_brush_size, width=5).pack(side="left")

        tk.Button(frame, text="⤺ Undo", command=self.undo).pack(side="left")
        tk.Button(frame, text="⤻ Redo", command=self.redo).pack(side="left")
        tk.Button(frame, text="グリッド ON/OFF", command=self.toggle_grid).pack(side="left")
        tk.Button(frame, text="💾 保存", command=self.save).pack(side="left")

    def set_mode(self, m):
        self.mode = m

    def choose_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.color = c

    def choose_fill(self):
        c = colorchooser.askcolor()[1]
        if c is not None:
            self.fill_color = c

    def change_brush_size(self):
        self.brush_size = int(self.brush_var.get())

    def toggle_grid(self):
        self.use_grid = not self.use_grid
        self.update_canvas()

    def change_font_size(self):
        self.font_size = self.font_var.get()
        self.text_font = tkFont.Font(family=self.font_family, size=self.font_size)

    # ---------------- Undo / Redo ----------------
    def push_undo(self):
        merged = self.merge_layers()
        # store a copy of merged image
        self.undo_stack.append(copy.deepcopy(merged))
        # clear redo stack per common behavior
        self.redo_stack = []

    def undo(self):
        if not self.undo_stack:
            return
        prev = self.undo_stack.pop()
        self.redo_stack.append(self.merge_layers())
        # replace current single merged layer approach:
        layer = Layer(self.w, self.h)
        layer.image = prev
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers = [layer]
        self.active_layer = 0
        self.update_canvas()

    def redo(self):
        if not self.redo_stack:
            return
        nxt = self.redo_stack.pop()
        self.undo_stack.append(self.merge_layers())
        layer = Layer(self.w, self.h)
        layer.image = nxt
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers = [layer]
        self.active_layer = 0
        self.update_canvas()

    # ---------------- 画像読み込み（レイヤーへ） ----------------
    def load_image_to_layer(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        img = Image.open(path).convert("RGBA")
        # リサイズは任意（ここではキャンバス全体に合わせる）
        img = img.resize((self.w, self.h))
        self.push_undo()
        layer = Layer(self.w, self.h)
        layer.image = img
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers.append(layer)
        self.active_layer = len(self.layers) - 1
        self.update_canvas()

    # ---------------- マウス操作 ----------------
    def on_press(self, event):
        # 保存用に undo push（ドラッグ操作の最初）
        self.push_undo()

        # クリック座標を画像座標に変換
        cx, cy = self.screen_to_canvas(event.x, event.y)
        # snap は画像座標に対して行う
        cx = self.snap(cx)
        cy = self.snap(cy)
        self.start_x, self.start_y = cx, cy

        # テキストモード：PIL に直接描画する（方式A）
        if self.mode == "text":
            txt = simpledialog.askstring("テキスト", "文字を入力:")
            if txt:
                cx = self.snap(self.start_x)
                cy = self.snap(self.start_y)

                # --- PIL に直接描画 ---
                draw = self.layers[self.active_layer].draw
                draw.text(
                    (cx, cy),
                    txt,
                    fill=self.color,
                    font=self.text_font  # ← 日本語＆サイズ対応フォント
                )
            self.update_canvas()
            return

        # 選択（方式A では編集不可だが placeholder）
        if self.mode == "select":
            # 方式A では描画を PIL に焼くため、Canvas オブジェクトは保持していません。
            # ここでは将来の拡張のために座標だけ取得して return します。
            return

        # 図形/描画/消しゴム はドラッグで行うのでここでは開始位置保存
        # そしてドラッグイベントで一時表示（canvas上）を行います。

    def on_drag(self, event):
        # 画面（イベント）座標 -> 画像座標
        x_raw, y_raw = self.screen_to_canvas(event.x, event.y)
        x = self.snap(x_raw)
        y = self.snap(y_raw)

        # フリーハンド描画（PIL レイヤーに直接描画）
        if self.mode == "draw":
            draw = self.layers[self.active_layer].draw
            draw.line([self.start_x, self.start_y, x, y],
                      fill=self.color, width=self.brush_size)
            self.start_x, self.start_y = x, y
            # すぐに表示更新
            self.update_canvas(show_temp=False)
            return

        # 消しゴム（PIL上で透明にする）
        if self.mode == "erase":
            draw = self.layers[self.active_layer].draw
            r = int(self.brush_size)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 0))
            self.start_x, self.start_y = x, y
            self.update_canvas(show_temp=False)
            return

        # 矩形 / 楕円 の一時プレビュー（Canvas に一時表示）
        if self.mode in ("rect", "oval"):
            # 削除してから作り直す（update_canvas は bg のみ差し替えるので temp_shape は残る）
            if self.temp_shape:
                try:
                    self.canvas.delete(self.temp_shape)
                except Exception:
                    pass

            sx_screen, sy_screen = self.canvas_to_screen(self.start_x, self.start_y)
            ex_screen, ey_screen = self.canvas_to_screen(x, y)

            if self.mode == "rect":
                self.temp_shape = self.canvas.create_rectangle(sx_screen, sy_screen, ex_screen, ey_screen,
                                                               outline=self.color, width=2, dash=(3,3))
            else:
                self.temp_shape = self.canvas.create_oval(sx_screen, sy_screen, ex_screen, ey_screen,
                                                          outline=self.color, width=2, dash=(3,3))
            # ここでは PIL には書き込みせず、表示のみ
            return

    def on_release(self, event):
        # リリース時の座標を取得してスナップ
        cx_raw, cy_raw = self.screen_to_canvas(event.x, event.y)
        cx = self.snap(cx_raw)
        cy = self.snap(cy_raw)

        # 矩形/楕円を確定して PIL に描く
        if self.mode in ("rect", "oval") and self.temp_shape:
            draw = self.layers[self.active_layer].draw
            shape = [self.start_x, self.start_y, cx, cy]
            # normalize coords for PIL (left,top,right,bottom)
            x0, y0 = min(shape[0], shape[2]), min(shape[1], shape[3])
            x1, y1 = max(shape[0], shape[2]), max(shape[1], shape[3])
            if self.mode == "rect":
                if self.fill_color:
                    draw.rectangle([x0, y0, x1, y1], outline=self.color, fill=self.fill_color, width=2)
                else:
                    draw.rectangle([x0, y0, x1, y1], outline=self.color, width=2)
            else:
                if self.fill_color:
                    draw.ellipse([x0, y0, x1, y1], outline=self.color, fill=self.fill_color, width=2)
                else:
                    draw.ellipse([x0, y0, x1, y1], outline=self.color, width=2)

            # 一時表示の削除
            try:
                self.canvas.delete(self.temp_shape)
            except Exception:
                pass
            self.temp_shape = None
            self.update_canvas()
            return

        # 選択モードの解除（方式Aでは編集しない）
        if self.mode == "select":
            return

    # ---------------- パン・ズーム ----------------
    def zoom_event(self, event):
        # Windows: event.delta, Linux: Button-4/5
        if hasattr(event, "delta"):
            scale = 1.1 if event.delta > 0 else 0.9
        else:
            # Mouse button 4/5 (some X11 setups)
            if event.num == 4:
                scale = 1.1
            else:
                scale = 0.9
        # zoom の中心を画面上のマウスポイントに合わせる（簡易）
        # 実装：ズーム倍率更新のみ（表示は update_canvas で反映）
        # より高度なアンカーズームが必要なら追加実装可
        self.zoom *= scale
        self.update_canvas()

    def pan_start(self, event):
        self.pan_x = event.x
        self.pan_y = event.y

    def pan_move(self, event):
        self.offset_x += event.x - self.pan_x
        self.offset_y += event.y - self.pan_y
        self.pan_x, self.pan_y = event.x, event.y
        self.update_canvas()

    # ---------------- 描画更新 ----------------
    def merge_layers(self):
        base = Image.new("RGBA", (self.w, self.h), (255, 255, 255, 255))  # 背景白
        for l in self.layers:
            base.alpha_composite(l.image)
        return base

    def update_canvas(self, show_temp=True):
        """Canvas 上の背景画像（タグ 'bg'）だけを差し替える実装に変更。
           こうすることで、temp_shape のような一時オブジェクトは Canvas 上に残る。
        """
        merged = self.merge_layers()
        # 表示サイズに合わせてリサイズ（ズーム）
        disp_w = max(1, int(self.w * self.zoom))
        disp_h = max(1, int(self.h * self.zoom))
        resized = merged.resize((disp_w, disp_h), resample=Image.BILINEAR)
        self.tk_img = ImageTk.PhotoImage(resized)

        # 背景画像だけ差し替える（タグ 'bg'）
        # 既存の bg を削除
        try:
            self.canvas.delete("bg")
        except Exception:
            pass

        self.canvas.create_image(self.offset_x, self.offset_y,
                                 image=self.tk_img, anchor="nw", tags=("bg",))

        # グリッドを描画（タグ 'grid'）
        self.canvas.delete("grid")
        if self.use_grid and self.grid_size > 0:
            step = int(self.grid_size * self.zoom)
            if step > 0:
                # 垂直線
                x_start = self.offset_x % step
                x = x_start
                while x < disp_w + abs(self.offset_x):
                    self.canvas.create_line(x, 0, x, disp_h + abs(self.offset_y), fill="#cccccc", tags=("grid",))
                    x += step
                # 水平線
                y_start = self.offset_y % step
                y = y_start
                while y < disp_h + abs(self.offset_y):
                    self.canvas.create_line(0, y, disp_w + abs(self.offset_x), y, fill="#cccccc", tags=("grid",))
                    y += step

        # note: temp_shape（プレビュー用）は delete("all") しないので残ります

    # ---------------- 保存 ----------------
    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("All files", "*.*")])
        if not path:
            return
        img = self.merge_layers()
        img.save(path)
        print("保存しました:", path)


if __name__ == "__main__":
    root = tk.Tk()
    Editor(root)
    root.mainloop()
