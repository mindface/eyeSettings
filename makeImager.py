import tkinter as tk
from tkinter import colorchooser, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageTk
import copy

class Layer:
    def __init__(self, w, h):
        self.image = Image.new("RGBA", (w, h), (0,0,0,0))
        self.draw = ImageDraw.Draw(self.image)
        self.selected_item = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.grid_size = 20
        self.use_grid = True

class Editor:
    def __init__(self, root):
        self.root = root
        self.root.title("多機能画像エディタ")

        self.w, self.h = 900, 650

        # --- グリッド設定 ---
        self.grid_size = 20
        self.use_grid = True

        # ---- レイヤー管理 ----
        self.layers = [Layer(self.w, self.h)]  # 背景レイヤー
        self.active_layer = 0                  # 描画先レイヤー

        # ---- Undo / Redo ----
        self.undo_stack = []
        self.redo_stack = []

        # ---- モード管理 ----
        self.mode = "draw"
        self.color = "black"
        self.fill_color = ""  # 塗りつぶし
        self.brush_size = 5

        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # ---- Canvas ----
        self.canvas = tk.Canvas(root, bg="gray", width=self.w, height=self.h)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.zoom_event)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)

        self.start_x = None
        self.start_y = None
        self.temp_shape = None

        self.create_ui()
        self.update_canvas()

    # ---------------- グリッドスナップ ----------------
    def snap(self, v):
        return round(v / self.grid_size) * self.grid_size if self.use_grid else v

    # ---------------- UI ----------------
    def create_ui(self):
        frame = tk.Frame(self.root)
        frame.pack()

        tk.Button(frame, text="🖊 描画", command=lambda: self.set_mode("draw")).pack(side="left")
        tk.Button(frame, text="🧽 消しゴム", command=lambda: self.set_mode("erase")).pack(side="left")
        tk.Button(frame, text="▭ 四角形", command=lambda: self.set_mode("rect")).pack(side="left")
        tk.Button(frame, text="◯ 丸", command=lambda: self.set_mode("oval")).pack(side="left")
        tk.Button(frame, text="🔤 テキスト", command=lambda: self.set_mode("text")).pack(side="left")
        tk.Button(frame, text="🎨 色", command=self.choose_color).pack(side="left")
        tk.Button(frame, text="塗りつぶし色", command=self.choose_fill).pack(side="left")
        tk.Button(frame, text="📷 画像読み込み", command=self.load_image).pack(side="left")

        # ブラシサイズ
        self.brush_var = tk.IntVar(value=5)
        tk.Spinbox(frame, from_=1, to=50, textvariable=self.brush_var,
                   command=self.change_brush_size, width=5).pack(side="left")

        tk.Button(frame, text="⤺ Undo", command=self.undo).pack(side="left")
        tk.Button(frame, text="⤻ Redo", command=self.redo).pack(side="left")
        tk.Button(frame, text="💾 保存", command=self.save).pack(side="left")

    def set_mode(self, m):
        self.mode = m

    def choose_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.color = c

    def choose_fill(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.fill_color = c

    def change_brush_size(self):
        self.brush_size = self.brush_var.get()

    # ---------------- Undo / Redo ----------------
    def push_undo(self):
        img = self.merge_layers()
        self.undo_stack.append(copy.deepcopy(img))
        self.redo_stack = []

    def undo(self):
        if not self.undo_stack:
            return
        img = self.undo_stack.pop()
        self.redo_stack.append(self.merge_layers())
        layer = Layer(self.w, self.h)
        layer.image = img
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers = [layer]
        self.update_canvas()

    def redo(self):
        if not self.redo_stack:
            return
        img = self.redo_stack.pop()
        self.undo_stack.append(self.merge_layers())
        layer = Layer(self.w, self.h)
        layer.image = img
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers = [layer]
        self.update_canvas()

    # ---------------- 画像読み込み ----------------
    def load_image(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        img = Image.open(path).convert("RGBA")
        img = img.resize((self.w, self.h))
        self.push_undo()
        img_tk = ImageTk.PhotoImage(img)
        item = self.canvas.create_image(
            self.offset_x,
            self.offset_y,
            image=img_tk,
            anchor="nw",
            tag="object"
        )
        self.canvas.images.append(img_tk)

        layer = Layer(self.w, self.h)
        layer.image = img
        layer.draw = ImageDraw.Draw(layer.image)
        self.layers.append(layer)
        self.active_layer = len(self.layers) - 1
        self.update_canvas()

    # ---------------- マウス操作 ----------------
    def screen_to_canvas(self, x, y):
        return int((x - self.offset_x) / self.zoom), int((y - self.offset_y) / self.zoom)

    def on_press(self, event):
        self.push_undo()
        self.start_x, self.start_y = self.screen_to_canvas(event.x, event.y)

        if self.mode == "text":
            txt = simpledialog.askstring("テキスト", "文字を入力:")
            cx = self.snap(self.start_x)
            cy = self.snap(self.start_y)
            item = self.canvas.create_text(
                cx * self.zoom + self.offset_x,
                cy * self.zoom + self.offset_y,
                text=txt,
                fill=self.color,
                anchor="nw",
                tag="object"
            )
            self.selected_item = item
            self.dragging = True
            self.update_canvas()
        if self.mode == "select":
            item = self.canvas.find_closest(event.x, event.y)
            if item:
                self.selected_item = item[0]
                bx, by = self.canvas.coords(self.selected_item)
                self.drag_offset_x = event.x - bx
                self.drag_offset_y = event.y - by
                return

    def on_drag(self, event):
        x, y = self.screen_to_canvas(event.x, event.y)

        if self.mode == "draw":
            draw = self.layers[self.active_layer].draw
            draw.line([self.start_x, self.start_y, x, y],
                      fill=self.color, width=self.brush_size)
            self.start_x, self.start_y = x, y

        elif self.mode == "erase":
            draw = self.layers[self.active_layer].draw
            draw.ellipse(
                [x - self.brush_size, y - self.brush_size,
                 x + self.brush_size, y + self.brush_size],
                fill=(0, 0, 0, 0)
            )

        elif self.mode in ("rect", "oval"):
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)

            sx, sy = self.start_x, self.start_y

            if self.mode == "rect":
                self.temp_shape = self.canvas.create_rectangle(
                    sx*self.zoom+self.offset_x, sy*self.zoom+self.offset_y,
                    x*self.zoom+self.offset_x, y*self.zoom+self.offset_y,
                    outline=self.color, width=2
                )
            else:
                self.temp_shape = self.canvas.create_oval(
                    sx*self.zoom+self.offset_x, sy*self.zoom+self.offset_y,
                    x*self.zoom+self.offset_x, y*self.zoom+self.offset_y,
                    outline=self.color, width=2
                )

        if self.mode == "select" and self.selected_item:
            nx = event.x - self.drag_offset_x
            ny = event.y - self.drag_offset_y

            # スナップ
            nx = self.snap(nx)
            ny = self.snap(ny)

            self.canvas.coords(self.selected_item, nx, ny)
            return

        self.update_canvas(show_temp=False)

    def on_release(self, event):
        if self.mode in ("rect", "oval") and self.temp_shape:
            x, y = self.screen_to_canvas(event.x, event.y)
            draw = self.layers[self.active_layer].draw
            shape = [self.start_x, self.start_y, x, y]

            if self.mode == "rect":
                draw.rectangle(shape, outline=self.color, fill=self.fill_color, width=2)
            else:
                draw.ellipse(shape, outline=self.color, fill=self.fill_color, width=2)

            self.canvas.delete(self.temp_shape)
            self.temp_shape = None
            self.update_canvas()

        if self.mode == "select":
            self.selected_item = None
            return

    # ---------------- パン・ズーム ----------------
    def zoom_event(self, event):
        scale = 1.1 if event.delta > 0 else 0.9
        self.zoom *= scale
        self.update_canvas()

    def pan_start(self, event):
        self.pan_x, self.pan_y = event.x, event.y

    def pan_move(self, event):
        self.offset_x += event.x - self.pan_x
        self.offset_y += event.y - self.pan_y
        self.pan_x, self.pan_y = event.x, event.y
        self.update_canvas()

    # ---------------- 描画更新 ----------------
    def merge_layers(self):
        base = Image.new("RGBA", (self.w, self.h), "white")
        for l in self.layers:
            base.alpha_composite(l.image)
        return base

    def update_canvas(self, show_temp=True):
        merged = self.merge_layers()
        resized = merged.resize((int(self.w*self.zoom), int(self.h*self.zoom)))
        self.tk_img = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y,
                                 image=self.tk_img, anchor="nw")

        if show_temp and self.temp_shape:
            pass

    # ---------------- 保存 ----------------
    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".png")
        if not path:
            return
        img = self.merge_layers()
        img.save(path)
        print("保存しました:", path)


if __name__ == "__main__":
    root = tk.Tk()
    Editor(root)
    root.mainloop()
